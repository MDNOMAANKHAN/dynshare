# Spotify-Weekly_Save
The code allows you to save all your Discover Weekly playlists in a permanent playlist.

# Spotify Playlist Saver

Spotify Playlist Saver is a Flask web application that allows users to save their Discover Weekly songs to a dedicated playlist named "Saved Weekly."

## Features

- **Authorization:** Uses Spotify OAuth for user authentication.
- **Playlist Management:** Automatically identifies Discover Weekly and Saved Weekly playlists. Creates the "Saved Weekly" playlist if not found.
- **Track Saving:** Adds the tracks from Discover Weekly to the Saved Weekly playlist.

## Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/spotify-playlist-saver.git
   cd spotify-playlist-saver
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Spotify API:**
   - Create a Spotify Developer account and create a new application to obtain the client ID and client secret.
   - Add the redirect URI in the Spotify Developer Dashboard.

4. **Update Configuration:**
   - Open `app.py` and replace `'YOUR_CLIENT_ID'`, `'YOUR_CLIENT_SECRET'`, and `'YOUR_RANDOM_SECRET_KEY'` with your actual values.

5. **Run the Application:**
   ```bash
   python app.py
   ```

6. **Access the Application:**
   Open your web browser and navigate to [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Usage

1. Click on the provided link to authorize the application with your Spotify account.
2. Once authorized, the application will redirect you, and you can click on "Save Discover Weekly" to save your Discover Weekly songs to the "Saved Weekly" playlist.

## Contributions

Contributions are welcome! If you have any improvements or suggestions, feel free to create an issue or submit a pull request.
