from shazamio import Shazam
import os

async def identify_track(file_path):
    shazam = Shazam()
    out = await shazam.recognize_song(file_path)
    if out and 'track' in out:
        return {
            'title': out['track']['title'],
            'author': out['track']['subtitle']
        }
    return None
