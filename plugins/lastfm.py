# -*- coding: utf-8 -*-


import json
import os
import time

base_url = "http://ws.audioscrobbler.com/2.0/?method={}&api_key={}&format=json"
api_key = None
try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def main(tg):
    global api_key
    api_key = tg.config['LASTFM']['api_key']
    if not api_key:
        return
    if tg.message:
        handle_message(tg)
    elif tg.inline_query:
        handle_inline_query(tg)


def handle_message(tg):
    tg.send_chat_action('typing')
    if tg.message['flagged_message']:
        link_profile(tg)
    else:
        first_name, lastfm_name, determiner = determine_names(tg)
        if lastfm_name:
            if tg.message['matched_regex'] in arguments['text'][:2]:
                response = last_played(tg.http, first_name, lastfm_name)
                if response:
                    message = response['text']
                    tg.send_message(message, reply_markup=tg.inline_keyboard_markup(response['keyboard']))
                else:
                    tg.send_message("No recently played tracks :(")
            elif tg.message['matched_regex'] in arguments['text'][:5]:
                top_tracks(tg, first_name, lastfm_name)
            else:
                top_artists(tg, first_name, lastfm_name)
        else:
            tg.send_message("It seems {} LastFM hasn't been linked\n"
                            "Reply with your LastFM to link it!".format(determiner), flag_message=True)


def handle_inline_query(tg):
    first_name, lastfm_name, determiner = determine_names(tg)
    boxes = list()
    if lastfm_name:
        track_list = get_recently_played(tg.http, lastfm_name, 8)
        for index, track in enumerate(track_list):
            if track['now_playing']:
                time_played = "Currently Playing!"
                message = "{} is currently listening to:\n".format(first_name)
            else:
                time_played = how_long(track['date'])
                if index == 0:
                    message = "{} last listened to:\n".format(first_name)
                else:
                    message = "{} has recently listened to:\n".format(first_name)
            message += "{}\t-\t{}".format(track['name'], track['artist'])
            message_contents = tg.input_text_message_content(message)
            keyboard = create_keyboard(lastfm_name, track['song_url'])
            boxes.append(tg.inline_query_result_article(track['name'], message_contents, description=time_played,
                                                        reply_markup=tg.inline_keyboard_markup(keyboard),
                                                        thumb_url=track['image']))
        is_personal = False if '(.*)' in tg.inline_query['matched_regex'] else True
        tg.answer_inline_query(boxes, is_personal=is_personal, cache_time=15)


def last_played(http, first_name, lastfm_name):
    track_list = get_recently_played(http, lastfm_name, 1)
    if track_list:
        for track in track_list:
            if track['now_playing']:
                message = "{} is currently listening to:\n".format(first_name)
            else:
                message = "{} last listened to:\n".format(first_name)
            message += "{}\t-\t{}".format(track['name'], track['artist'])
            keyboard = create_keyboard(lastfm_name, track['song_url'])
            return {'text': message, 'keyboard': keyboard}


def top_tracks(tg, first_name, lastfm_name):
    limit = int(tg.message['match'][1]) if tg.message['matched_regex'] in arguments['text'][3] else 8
    limit = 25 if limit > 25 else limit
    track_list = get_top_tracks(tg.http, lastfm_name, limit)
    if track_list:
        message = "<b>{}'s Top Tracks</b>\n".format(first_name)
        for track in track_list:
            message += '\n<a href="{}">{}</a>  -  <code>{} plays</code>'.format(track['song_url'], track['name'],
                                                                                track['play_count'])
        tg.send_message(message, disable_web_page_preview=True)


def top_artists(tg, first_name, lastfm_name):
    limit = int(tg.message['match'][1]) if tg.message['matched_regex'] in arguments['text'][6] else 8
    limit = 25 if limit > 25 else limit
    artists = get_top_artists(tg.http, lastfm_name, limit)
    if artists:
        message = "<b>{}'s Top Artists</b>\n".format(first_name)
        for artist in artists:
            message += '\n<a href="{}">{}</a>  -  <code>{} plays</code>'.format(artist['url'], artist['name'],
                                                                                artist['play_count'])
        tg.send_message(message, disable_web_page_preview=True)


def get_top_artists(local_http, user_name, limit, period='1month'):
    artist_list = list()
    method = 'user.getTopArtists'
    url = (base_url + '&user={}&limit={}&period={}').format(method, api_key, user_name, limit, period)
    result = local_http.request('GET', url).data
    response = json.loads(result.decode('UTF-8'))
    artists = response['topartists']['artist']
    for artist in artists:
        info = {
            'name': artist['name'],
            'play_count': artist['playcount'],
            'url': artist['url'],
        }
        artist_list.append(info)
    return artist_list


def get_top_tracks(local_http, user_name, limit, period='1month'):
    track_list = list()
    method = 'user.getTopTracks'
    url = (base_url + '&user={}&limit={}&period={}').format(method, api_key, user_name, limit, period)
    result = local_http.request('GET', url).data
    response = json.loads(result.decode('UTF-8'))
    tracks = response['toptracks']['track']
    for track in tracks:
        song = {
            'name': track['name'],
            'play_count': track['playcount'],
            'artist': track['artist']['name'],
            'song_url': track['url'],
            'artist_url': track['artist']['url']
        }
        track_list.append(song)
    return track_list


def get_recently_played(local_http, user_name, limit):
    method = 'user.getRecentTracks'
    url = (base_url + '&user={}&limit={}').format(method, api_key, user_name, limit)
    result = local_http.request('GET', url).data
    response = json.loads(result.decode('UTF-8'))
    if 'error' in response:
        return
    tracks = response['recenttracks']['track']
    track_list = list()
    for track in tracks:
        if '@attr' in track:
            now_playing = True
        else:
            now_playing = False
        song = {
            'name': track['name'],
            'artist': track['artist']['#text'],
            'song_url': track['url'],
            'album': track['album']['#text'],
            'now_playing': now_playing,
            'image': track['image'][-1]['#text']

        }
        try:
            song['date'] = track['date']['uts']
        except KeyError:
            song['date'] = None
        track_list.append(song)
    return track_list


def get_lastfm_username(user_id):
    try:
        with open('data/profile/{}.json'.format(user_id)) as json_file:
            profile = json.load(json_file)
    except FileNotFoundError:
        return
    if 'lastfm' in profile:
        return profile['lastfm']


def determine_names(tg):
    matched_regex = tg.message['matched_regex'] if tg.message else tg.inline_query['matched_regex']
    if '(.*)' in matched_regex:
        determiner = None
        lastfm_name = first_name = tg.message['match'] if tg.message else tg.inline_query['match']
    elif tg.message and 'reply_to_message' in tg.message:
        user_id = tg.message['reply_to_message']['from']['id']
        determiner = "this"
        lastfm_name = get_lastfm_username(user_id)
        first_name = tg.message['reply_to_message']['from']['first_name']
    else:
        user_id = tg.message['from']['id'] if tg.message else tg.inline_query['from']['id']
        determiner = "your"
        lastfm_name = get_lastfm_username(user_id)
        first_name = tg.message['from']['first_name'] if tg.message else tg.inline_query['from']['first_name']
    return first_name, lastfm_name, determiner


def link_profile(tg):
    if not os.path.exists('data/profile'):
        os.makedirs('data/profile')
    user_id = tg.message['from']['id']
    try:
        with open('data/profile/{}.json'.format(user_id)) as file:
            profile = json.load(file)
    except (JSONDecodeError, FileNotFoundError):
        open('data/profile/{}.json'.format(user_id), 'w')
        profile = dict()
    if tg.message['text']:
        if 'lastfm' in profile:
            message = "Updated your LastFM!"
        else:
            message = "Successfully set your LastFM!"
        profile['lastfm'] = tg.message['text'].replace('\n', '')
        track_list = get_recently_played(tg.http, profile['lastfm'], 1)
        keyboard = [[]]
        if track_list:
            track_list = track_list.pop()
            if track_list['now_playing']:
                message += "\n\nYou are currently listening to:"
            else:
                message += "\n\nYou have last listened to:"
            message += "\n{} - {}".format(track_list['name'], track_list['artist'])
            keyboard = create_keyboard(profile['lastfm'], track_list['song_url'])
        tg.send_message(message, reply_markup=tg.inline_keyboard_markup(keyboard))
    else:
        tg.send_message("Invalid username")
    with open('data/profile/{}.json'.format(user_id), 'w') as file:
        json.dump(profile, file, sort_keys=True, indent=4)


def create_keyboard(lastfm_name, song_url):
    profile_url = "http://www.lastfm.com/user/{}".format(lastfm_name)
    return [[{'text': "Profile", 'url': profile_url}, {'text': "Song", 'url': song_url}]]


def how_long(epoch_time):
    if epoch_time:
        diff = int(time.time() - int(epoch_time))
        if diff < 240:
            return "Just now"
        elif diff < 3600:
            return "{} minutes ago".format(int(diff / 60))
        elif 86399 > diff > 3600:
            return "{} hours ago".format(int(diff / 3600))
        elif diff > 86400:
            return "{} days ago".format(int(diff / 86400))
    else:
        return "Unknown time ago"


parameters = {
    'name': "LastFM",
    'short_description': "View your recently played LastFM tracks!",
    'long_description': "This plugin allows you to view and share metrics related to your LastFM account. Simply use "
                        "/lastfm to share your last played track, /toptracks for your most played songs, or /topartists"
                        " for your most played artists. The commands also works with a specified username or by reply "
                        "to another users message.",
    'permissions': True
}

arguments = {
    'text': [
        "^/lastfm (.*)",
        "^/lastfm$",
        "^/toptracks$",
        u"^/toptracks (--|\u2014)(\d+)$",
        "^/toptracks (.*)",
        "^/topartists$",
        u"^/topartists (--|\u2014)(\d+)$",
        "^/topartists (.*)"
    ]
}

inline_arguments = [
    '^lastfm$',
    "^lastfm (.*)",
    "^lastfm (.*)",
    "^/lastfm$",
]
