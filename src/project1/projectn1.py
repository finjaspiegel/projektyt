from googleapiclient.discovery import build
import re

API_KEY = "AIzaSyAaWgzmlZq1wCvkBJ0TaAzCTg1lczKXjzY"
youtube = build("youtube", "v3", developerKey=API_KEY)

def extract_channel_id(channel_input):
    """
    Extrahiert die Kanal-ID aus einem Link, Handle (@name) oder Kanalnamen.
    """
    if "youtube.com/channel/" in channel_input:
        match = re.search(r"channel/([a-zA-Z0-9_-]+)", channel_input)
        return match.group(1) if match else None

    if "@" in channel_input:
        channel_input = channel_input.replace("https://www.youtube.com/", "").replace("@", "")

    request = youtube.search().list(
        q=channel_input,
        part="snippet",
        type="channel",
        maxResults=1
    )
    response = request.execute()
    if not response["items"]:
        print("Kanal nicht gefunden!")
        return None

    return response["items"][0]["id"]["channelId"]

def get_uploads_playlist_id(channel_id):
    """
    Ruft die Uploads-Playlist-ID des Kanals ab.
    """
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = request.execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_last_videos_with_stats(playlist_id, max_results=5):
    """
    Holt die letzten Videos aus der Uploads-Playlist, die länger als 3 Minuten sind,
    zusammen mit ihren Aufrufen und Likes. Berechnet den Durchschnitt der Aufrufe.
    """
    valid_videos = []
    next_page_token = None

    while len(valid_videos) < max_results:
        # Playlist-Items abrufen
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=10,  # Hole 10 Videos pro Anfrage
            pageToken=next_page_token
        )
        response = request.execute()

        # Abbruch, wenn keine weiteren Videos verfügbar sind
        if "items" not in response or not response["items"]:
            break

        video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]

        # Videodetails abrufen
        video_details_request = youtube.videos().list(
            part="contentDetails,snippet,statistics",
            id=",".join(video_ids)
        )
        video_details_response = video_details_request.execute()

        for video in video_details_response["items"]:
            duration = video["contentDetails"]["duration"]
            title = video["snippet"]["title"]
            video_id = video["id"]
            statistics = video["statistics"]

            # Dauer in Sekunden berechnen
            if "PT" in duration:
                minutes = int(re.search(r"(\d+)M", duration).group(1)) if "M" in duration else 0
                seconds = int(re.search(r"(\d+)S", duration).group(1)) if "S" in duration else 0
                total_seconds = minutes * 60 + seconds

                # Filter: Nur Videos länger als 3 Minuten
                if total_seconds >= 180:
                    # Extrahiere Aufrufe und Likes (falls vorhanden)
                    views = int(statistics.get("viewCount", 0))
                    likes = int(statistics.get("likeCount", 0))
                    valid_videos.append((title, video_id, total_seconds, views, likes))

                    # Abbruch, wenn genug Videos gefunden wurden
                    if len(valid_videos) == max_results:
                        break

        # Nächste Seite laden
        next_page_token = response.get("nextPageToken", None)
        if not next_page_token:
            break

    # Ergebnis anzeigen
    print("\nDie letzten Videos (länger als 3 Minuten):")
    total_views = 0
    if valid_videos:
        for title, video_id, total_seconds, views, likes in valid_videos:
            total_views += views
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            print(f"- {title} (Dauer: {minutes} Minuten {seconds} Sekunden, Aufrufe: {views}, Likes: {likes}) - https://www.youtube.com/watch?v={video_id}")
        
        # Durchschnittliche Aufrufe berechnen
        average_views = total_views / len(valid_videos)
        print(f"\nDurchschnittliche Aufrufe der letzten {len(valid_videos)} Videos: {average_views:.2f}")
    else:
        print("Keine Videos gefunden, die länger als 3 Minuten sind.")

if __name__ == "__main__":
    channel_input = input("Gib den YouTube-Kanal-Link, Handle (@name) oder Namen ein: ")
    channel_id = extract_channel_id(channel_input)
    if channel_id:
        playlist_id = get_uploads_playlist_id(channel_id)
        get_last_videos_with_stats(playlist_id)
    else:
        print("Fehler: Kanal konnte nicht gefunden werden.")


