import streamlit as st
from googleapiclient.discovery import build
import re

# YouTube API einrichten
API_KEY = "AIzaSyAaWgzmlZq1wCvkBJ0TaAzCTg1lczKXjzY"
youtube = build("youtube", "v3", developerKey=API_KEY)

def extract_channel_id(channel_input):
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
        return None

    return response["items"][0]["id"]["channelId"]

def get_uploads_playlist_id(channel_id):
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = request.execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_videos_with_stats(playlist_id, max_results=5):
    valid_videos = []
    next_page_token = None

    while len(valid_videos) < max_results:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=10,
            pageToken=next_page_token
        )
        response = request.execute()

        if "items" not in response or not response["items"]:
            break

        video_ids = [item["contentDetails"]["videoId"] for item in response["items"]]

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

            if "PT" in duration:
                minutes = int(re.search(r"(\d+)M", duration).group(1)) if "M" in duration else 0
                seconds = int(re.search(r"(\d+)S", duration).group(1)) if "S" in duration else 0
                total_seconds = minutes * 60 + seconds

                if total_seconds >= 180:
                    views = int(statistics.get("viewCount", 0))
                    likes = int(statistics.get("likeCount", 0))
                    valid_videos.append((title, video_id, total_seconds, views, likes))

                    if len(valid_videos) == max_results:
                        break

        next_page_token = response.get("nextPageToken", None)
        if not next_page_token:
            break

    return valid_videos

# Streamlit-Interface
st.title("YouTube Channel Dashboard")

channel_input = st.text_input("Gib den YouTube-Kanal-Link, Handle (@name) oder Namen ein:")
max_results = st.slider("Anzahl der Videos", min_value=1, max_value=20, value=5)

if channel_input:
    st.write("Daten abrufen...")
    channel_id = extract_channel_id(channel_input)
    if channel_id:
        playlist_id = get_uploads_playlist_id(channel_id)
        videos = get_videos_with_stats(playlist_id, max_results)

        if videos:
            total_views = sum(video[3] for video in videos)
            average_views = total_views / len(videos)

            st.subheader("Statistiken:")
            st.write(f"Durchschnittliche Aufrufe: {average_views:.2f}")
            st.write(f"Gesamtaufrufe: {total_views}")

            st.subheader("Videos:")
            for title, video_id, total_seconds, views, likes in videos:
                st.write(f"- [{title}](https://www.youtube.com/watch?v={video_id}) - "
                         f"Aufrufe: {views}, Likes: {likes}")
        else:
            st.warning("Keine Videos gefunden, die länger als 3 Minuten sind.")
    else:
        st.error("Kanal konnte nicht gefunden werden.")
