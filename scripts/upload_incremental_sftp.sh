#!/usr/bin/env bash

set -euo pipefail

package_path="${1:-}"
required_names=(
  NEWS_SFTP_HOST
  NEWS_SFTP_USER
  NEWS_SFTP_PRIVATE_KEY
  NEWS_SFTP_KNOWN_HOSTS
)

configured=false
for name in "${required_names[@]}"; do
  if [[ -n "${!name:-}" ]]; then
    configured=true
    break
  fi
done

if [[ "$configured" == false ]]; then
  echo "[SFTP] Server secrets are not configured; skipping upload."
  exit 0
fi

for name in "${required_names[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "[SFTP] Missing required secret: $name" >&2
    exit 1
  fi
done

if [[ ! -s "$package_path" ]]; then
  echo "[SFTP] Incremental package is missing or empty: $package_path" >&2
  exit 1
fi

port="${NEWS_SFTP_PORT:-22}"
remote_dir="${NEWS_SFTP_REMOTE_DIR:-incoming/news}"
remote_dir="${remote_dir%/}"

if [[ ! "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
  echo "[SFTP] NEWS_SFTP_PORT must be between 1 and 65535." >&2
  exit 1
fi
if [[ ! "$NEWS_SFTP_USER" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "[SFTP] NEWS_SFTP_USER contains unsupported characters." >&2
  exit 1
fi
if [[ ! "$remote_dir" =~ ^[A-Za-z0-9_./-]+$ ]] || [[ "$remote_dir" == *".."* ]]; then
  echo "[SFTP] NEWS_SFTP_REMOTE_DIR contains unsupported path characters." >&2
  exit 1
fi

run_id="${GITHUB_RUN_ID:-manual}"
run_attempt="${GITHUB_RUN_ATTEMPT:-1}"
timestamp="$(TZ=Asia/Shanghai date +%Y%m%dT%H%M%S%z)"
remote_name="news-incremental-${timestamp}-run${run_id}-attempt${run_attempt}.json.gz"

temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
private_key_path="$temp_dir/id_sftp"
known_hosts_path="$temp_dir/known_hosts"
checksum_path="$temp_dir/${remote_name}.sha256"
batch_path="$temp_dir/sftp.batch"

umask 077
printf '%s\n' "$NEWS_SFTP_PRIVATE_KEY" | tr -d '\r' >"$private_key_path"
printf '%s\n' "$NEWS_SFTP_KNOWN_HOSTS" | tr -d '\r' >"$known_hosts_path"

if command -v sha256sum >/dev/null 2>&1; then
  checksum="$(sha256sum "$package_path" | awk '{print $1}')"
else
  checksum="$(shasum -a 256 "$package_path" | awk '{print $1}')"
fi
printf '%s  %s\n' "$checksum" "$remote_name" >"$checksum_path"

remote_part="$remote_dir/.${remote_name}.part"
checksum_part="$remote_dir/.${remote_name}.sha256.part"
{
  printf 'put "%s" "%s"\n' "$package_path" "$remote_part"
  printf 'put "%s" "%s"\n' "$checksum_path" "$checksum_part"
  printf 'rename "%s" "%s/%s"\n' "$remote_part" "$remote_dir" "$remote_name"
  printf 'rename "%s" "%s/%s.sha256"\n' "$checksum_part" "$remote_dir" "$remote_name"
} >"$batch_path"

sftp_args=(
  -b "$batch_path"
  -i "$private_key_path"
  -P "$port"
  -o BatchMode=yes
  -o ConnectTimeout=20
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$known_hosts_path"
)

for attempt in 1 2 3; do
  if sftp "${sftp_args[@]}" "$NEWS_SFTP_USER@$NEWS_SFTP_HOST"; then
    echo "[SFTP] Uploaded $remote_dir/$remote_name"
    exit 0
  fi
  if ((attempt < 3)); then
    echo "[SFTP] Upload attempt $attempt failed; retrying..." >&2
    sleep $((attempt * 5))
  fi
done

echo "[SFTP] Upload failed after 3 attempts." >&2
exit 1
