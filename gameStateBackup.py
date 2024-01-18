import os
import sys
import re
import zipfile
import datetime
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# Load environment variables from .env file
load_dotenv()

# Configuration variables
SAVE_DIRECTORY = os.getenv('SAVE_DIRECTORY', 'ProjectWar/Saved')
MAX_STATES = int(os.getenv('MAX_STATES', 5))
RECYCLE = os.getenv('RECYCLE', 'False').lower() == 'true'
CHECK_INTEGRITY = os.getenv('CHECK_INTEGRITY', 'False').lower() == 'true'
COMPRESSION_LEVEL = int(os.getenv('COMPRESSION_LEVEL', 6))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'nil')
AVATAR_URL = os.getenv('AVATAR_URL', 'None')
DISCORD_USER = os.getenv('DISCORD_USER', 'None')
BACKUP_DIRECTORY = os.getenv('BACKUP_DIRECTORY', Path(__file__).parent / 'Backups')

backup_directory = Path(BACKUP_DIRECTORY)
backup_directory.mkdir(parents=True, exist_ok=True)

# Logging
logger = logging.getLogger('backup_logger')
logger.setLevel(logging.INFO)
log_file = Path(__file__).with_name('backup.log')
handler = RotatingFileHandler(log_file, maxBytes=10**6, backupCount=5)
handler.setFormatter(logging.Formatter
                     ('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def send_discord_message(WEBHOOK_URL, message, DISCORD_USER, AVATAR_URL):
    payload = {
        "content": message,
        "username": DISCORD_USER,
        "avatar_url": AVATAR_URL
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    response = requests.post(WEBHOOK_URL, json=payload)

    if response.status_code == 204:
        print("Message sent successfully")
    else:
        print(f"Failed to send message. Response: {response.text}")


def archive_existing_backup():
    existing_backup = None
    archive_pattern = re.compile(r'GameStates_[AP]M_Archive_\d{14}\.zip')
    for file in backup_directory.glob('GameStates_*.zip'):
        if archive_pattern.match(file.name):
            continue
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        archived_name = file.stem + f"_Archive_{timestamp}" + file.suffix
        archived_file = backup_directory / archived_name
        file.rename(archived_file)
        existing_backup = archived_file
    return existing_backup


def find_newest_game_state_directories(save_dir, max_states):
    game_state_dirs = sorted([d for d in save_dir.glob
                              ('GameStates_*') if d.is_dir()],
                             key=lambda x: x.stat().st_mtime, reverse=True)
    return game_state_dirs[:max_states]


def create_backup_zip(directories, suffix):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    zip_name = f"GameStates_{suffix}_{timestamp}.zip"
    zip_path = backup_directory / zip_name
    compression = zipfile.ZIP_DEFLATED if COMPRESSION_LEVEL > 0 else zipfile.ZIP_STORED
    with zipfile.ZipFile(zip_path, 'w', compression=compression,
                         compresslevel=COMPRESSION_LEVEL) as zipf:
        for dir in directories:
            for root, _, files in os.walk(dir):
                for file in files:
                    file_path = Path(root) / file
                    zipf.write(file_path,
                               arcname=file_path.relative_to(SAVE_DIRECTORY))
    return zip_path


def check_zip_file_integrity(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        return zipf.testzip() is None


def upload_to_backblaze(file_path, bucket_name):
    account_info = InMemoryAccountInfo()
    b2_api = B2Api(account_info)
    b2_api.authorize_account("production", os.getenv('B2_APPLICATION_KEY_ID'),
                             os.getenv('B2_APPLICATION_KEY'))

    bucket = b2_api.get_bucket_by_name(bucket_name)

    b2_file = bucket.upload_local_file(
        local_file=file_path,
        file_name=file_path.name
    )

    return b2_file


def create_backup():
    save_dir = Path(SAVE_DIRECTORY)
    if not save_dir.exists():
        error_message = f"The save directory {save_dir} does not exist."
        logger.error(error_message)
        if WEBHOOK_URL != 'nil':
            send_discord_message(WEBHOOK_URL,
                                 error_message,
                                 DISCORD_USER,
                                 AVATAR_URL)
        raise FileNotFoundError(error_message)

    existing_backup = archive_existing_backup()

    newest_dirs = find_newest_game_state_directories(save_dir,
                                                     MAX_STATES)

    suffix = 'AM' if datetime.datetime.now().hour < 12 else 'PM'

    backup_zip = create_backup_zip(newest_dirs, suffix)

    if CHECK_INTEGRITY and not check_zip_file_integrity(backup_zip):
        error_message = "The backup zip file failed the integrity check."
        logger.error(error_message)
        if WEBHOOK_URL != 'nil':
            send_discord_message(WEBHOOK_URL, 
                                 error_message,
                                 DISCORD_USER,
                                 AVATAR_URL)
        raise ValueError(error_message)

    if RECYCLE and existing_backup:
        existing_backup.unlink()
        logger.info(f"Older backup file {existing_backup.name} has been deleted.")
        if WEBHOOK_URL != 'nil':
            send_discord_message(
                WEBHOOK_URL,
                f"Older backup file {existing_backup.name} has been deleted.",
                DISCORD_USER, AVATAR_URL
            )

    logger.info(f"Backup file created: {backup_zip}")
    if WEBHOOK_URL != 'nil':
        send_discord_message(
            WEBHOOK_URL, 
            ("Backup file created: " + str(backup_zip) +
             ", I am configured to store " + str(MAX_STATES) +
             " GameStates per backup run."),
            DISCORD_USER, AVATAR_URL)

    if os.getenv('CLOUD_BACKUPS', 'False').lower() == 'true':
        try:
            b2_file = upload_to_backblaze(
                file_path=backup_zip,
                bucket_name=os.getenv('B2_BUCKET_NAME')
            )
            success_message = f"File uploaded to Backblaze Bucket"
            logger.info(success_message)
            if WEBHOOK_URL != 'nil':
                send_discord_message(WEBHOOK_URL,
                                     success_message,
                                     DISCORD_USER,
                                     AVATAR_URL)
        except Exception as e:
            error_message = f"Failed to upload to Backblaze: {e}"
            logger.error(error_message)
            if WEBHOOK_URL != 'nil':
                send_discord_message(WEBHOOK_URL,
                                     error_message,
                                     DISCORD_USER,
                                     AVATAR_URL)
            raise

    return backup_zip


if __name__ == '__main__':
    try:
        backup_zip_path = create_backup()
    except Exception as e:
        error_message = f"An error occurred: {e}"
        logger.error(error_message)
        if WEBHOOK_URL != 'nil':
            send_discord_message(WEBHOOK_URL,
                                 error_message,
                                 DISCORD_USER,
                                 AVATAR_URL)
        sys.exit(1)
