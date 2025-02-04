import os
import sys
from datetime import datetime, timedelta
from plexapi.server import PlexServer
import logging
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Configuration (consider loading from environment variables or a config file)
baseurl = ''
plex_login = ''  # Replace with your Plex login username
plex_password = ''  # Replace with your Plex login password
label_name_48h = "HOTFOR48H"  # Replace with your specific label for +48h
label_name_1month = "ADDED1MONTHAGO"  # Replace with your specific label for 1 month ago

# Calculate dates
default_addedAt_value = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
one_month_ago_value = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

def retrieve_plex_token():
    try:
        logging.info("Retrieving X-Plex-Token using Plex login/password...")

        # Request the X-Plex-Token
        response = requests.post(
            'https://plex.tv/users/sign_in.xml',
            auth=(plex_login, plex_password),
            headers={
                'X-Plex-Device-Name': 'PlexMediaServer',
                'X-Plex-Provides': 'server',
                'X-Plex-Version': '0.9',
                'X-Plex-Platform-Version': '0.9',
                'X-Plex-Platform': 'xcid',
                'X-Plex-Product': 'Plex Media Server',
                'X-Plex-Device': 'Linux',
                'X-Plex-Client-Identifier': 'XXXX',
            },
            params={'X-Plex-Token': ''}
        )

        # Extract X_PLEX_TOKEN from the response
        x_plex_token = response.text.split('<authentication-token>')[1].split('</authentication-token>')[0]

        if not x_plex_token:
            raise ValueError('Failed to retrieve X-Plex-Token.')

        logging.info(f'Your X_PLEX_TOKEN: {x_plex_token}')

        return x_plex_token

    except (requests.RequestException, ValueError) as e:
        logging.error(f"Failed to retrieve Plex token: {e}")
        sys.exit(1)

def connect_to_plex(baseurl, token):
    try:
        return PlexServer(baseurl, token)
    except Exception as e:
        logging.error(f"Failed to connect to Plex server: {e}")
        sys.exit(1)

def update_videos_or_shows(library, label_name, new_addedAt_value):
    try:
        # Get all items (movies or shows) with the specified label
        items = library.search(label=label_name)
    except Exception as e:
        logging.error(f"Failed to retrieve items with label '{label_name}': {e}")
        return

    # Prepare updates
    updates = {"addedAt.value": new_addedAt_value}

    # Iterate over labeled items, update them, and remove the label
    for item in items:
        try:
            if item.type == 'movie':
                # Update the addedAt.value for the movie
                item.edit(**updates)
                logging.info(f"Successfully updated metadata for movie '{item.title}' with {updates}")
            elif item.type == 'show':
                # Update the addedAt.value for the show
                item.edit(**updates)
                logging.info(f"Successfully updated metadata for show '{item.title}' with {updates}")

                # Update the addedAt.value for each episode of the show
                for episode in item.episodes():
                    episode.edit(**updates)
                    logging.info(f"Successfully updated metadata for episode '{episode.title}' with {updates}")

            # Remove the label from the item
            item.removeLabel(label_name)
            logging.info(f"Successfully removed label '{label_name}' from item '{item.title}'")
        except Exception as e:
            logging.error(f"Failed to update or remove label from item '{item.title}': {e}")

# Main execution
if __name__ == "__main__":
    try:
        # Retrieve Plex token
        token = retrieve_plex_token()

        # Connect to Plex server
        plex = connect_to_plex(baseurl, token)

        # Loop through all libraries to handle both movies and TV shows
        for library in plex.library.sections():
            # Update movies and shows with +48h label
            update_videos_or_shows(library, label_name_48h, default_addedAt_value)

            # Update movies and shows with 1 month ago label
            update_videos_or_shows(library, label_name_1month, one_month_ago_value)

    except KeyboardInterrupt:
        logging.info("Process interrupted by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
