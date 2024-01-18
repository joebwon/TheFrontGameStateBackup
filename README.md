# Backup Script for The Front Game States

This Python script automates the process of creating backups for game state directories and optionally uploads them to a Backblaze B2 bucket.

I made this for my own purposes, and it's been tested on Windows Server 2022, but should work fine on other platforms.

We don't delete anything from ProjectWar/Saved/ when we run the backup, this is meant for disaster recovery rather than managing that.

## Recommendations
If using Backblaze storage, set your retention policies up so the saves automatically expire off. It is also highly recommended that you set an Object Lock on the bucket to at least 1 day, this will prevent your backups from being deleted and is a great feature - be careful with how long you set the Object Lock to because once a file is stored the object lock cannot be removed, so if you put 365 days, you're stuck with that file for a year unless you delete your account.

I run this as a scheduled task in the AM and PM

## Features

- Local backup creation with configurable maximum number of states
- Option to remove local backups, or keep them
- Integrity check of the backup zip file
- Optional cloud backup to Backblaze B2
- Logging to discord (or local file only)

## Configuration

The script is configured via environment variables that can be set in a `.env` file located in the same directory as the script.

### Environment Variables

- `SAVE_DIRECTORY`: The directory where game states are stored.
- `BACKUP_DIRECTORY`: The directory where backup zip files are placed.
- `MAX_STATES`: The maximum number of game states to include in a backup. The maximum number of Game States folders to add to the archive in a single execution.
- `RECYCLE`: Whether to delete older backups after creating a new one (`True` or `False`).
- `CHECK_INTEGRITY`: Whether to perform a zip integrity check (`True` or `False`).
- `COMPRESSION_LEVEL`: The compression level for the zip file (0-9). I use level 6, higher numbers = smaller archives but take more time and resources to compress.
- `WEBHOOK_URL`: The Discord webhook URL for sending notifications.
- `AVATAR_URL`: The avatar URL for the Discord messages. Pro-tip: You can post an image in a private discord channel and use it's link for the avatar.
- `DISCORD_USER`: The username for the Discord messages.
- `CLOUD_BACKUPS`: Whether to enable cloud backups (`True` or `False`).
- `B2_APPLICATION_KEY_ID`: Your Backblaze B2 application key ID.
- `B2_APPLICATION_KEY`: Your Backblaze B2 application key.
- `B2_BUCKET_NAME`: The name of your Backblaze B2 bucket.

If you prefer not to use Backblaze for cloud backups, and you're using a shared filesystem, OneDrive, or something like that, just use RECYCLE=False and the backed up files won't be removed. You'll of course need to manage how often to purge older backups, and if you don't have some way to prevent them from getting deleted (should say, your server be compromised) then the backups aren't actually that useful.

## Windows installation
For this part, I'll do the steps using a windows admin account. You can do things how you want to suit your environment.
Download and install python (https://www.python.org/downloads/windows/), note that there is an option in the installer to install for all users, if preferred. Make sure to select the following options:
- Install pip
- Add python to the environment
- Make python the default program to run .py files

If haven't already, upgrade pip and install setuptools:
- python -m pip install --upgrade pip
- pip install setuptools

Install the module requirements:
- pip install -r requirements.txt

## Usage

You can run the script manually with:
```python backup_script.py```

