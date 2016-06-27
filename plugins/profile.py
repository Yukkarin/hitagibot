# -*- coding: utf-8 -*-


import json
import os

import _mysql_exceptions

user_id = None
entries = None
try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def main(tg):
    global user_id, entries
    if not os.path.exists('data/profile'):
        os.makedirs('data/profile')
    if tg.message:
        tg.send_chat_action('typing')
        if 'reply_to_message' in tg.message:
            user_id = tg.message['reply_to_message']['from']['id']
        else:
            user_id = tg.message['from']['id']
    else:
        user_id = tg.inline_query['from']['id']
    with open('data/entries.json', 'r') as json_file:
        entries = json.load(json_file)
    if tg.message:
        if tg.message['matched_regex'] == arguments['text'][0]:
            message, keyboard = return_profile(tg)
            tg.send_message(message, reply_markup=tg.inline_keyboard_markup(keyboard))
        elif tg.message['matched_regex'] == arguments['text'][1]:
            if "delete" in tg.message['match'] or "del" in tg.message['match']:
                delete_entry(tg)
            else:
                add_entry(tg)
    else:
        message, keyboard = return_profile(tg)
        message_contents = tg.input_text_message_content(message)
        box = tg.inline_query_result_article("Share your profile!", message_contents,
                                             reply_markup=tg.inline_keyboard_markup(keyboard))
        tg.answer_inline_query([box], is_personal=True, cache_time=60)


def return_profile(tg):
    global user_id
    if tg.message:
        if 'reply_to_message' in tg.message:
            first_name = tg.message['reply_to_message']['from']['first_name']
        else:
            first_name = tg.message['from']['first_name']
    else:
        first_name = tg.inline_query['from']['first_name']
    try:
        with open('data/profile/{}.json'.format(user_id)) as json_file:
            profile = json.load(json_file)
    except (JSONDecodeError, FileNotFoundError):
        profile = dict()
    message = "<b>{}'s Profile</b>".format(first_name.title())
    keyboard = make_keyboard(profile)
    stats = get_stats(tg) if tg.message else None
    if stats:
        message += "\n<b>Total Messages:</b> {:,} ({})".format(stats['user_total'], stats['percentage'])
    try:
        playing = last_fm(tg.http, profile, tg.config['LASTFM']['api_key'])
    except KeyError:
        playing = None
    if playing:
        message += u"\n\U0001F3B6 {} - {}".format(playing['name'], playing['artist'])
    if len(message.split('\n')) == 1 and not keyboard:
        message = "\nYour profile seems empty. You can add entries using:\n<code>/profile website username</code>"
    return message, keyboard


def make_keyboard(profile):
    remaining = len(profile)
    keyboard = []
    for name, username in profile.items():
        row_length = 3 if remaining >= 3 or remaining == 1 else 2
        pretty_name = entries[name]['pretty_name']
        url = entries[name]['url'].format(username)
        button = {'text': pretty_name, 'url': url}
        if keyboard and len(keyboard[-1]) < row_length:
            keyboard[-1].append(button)
        else:
            keyboard.append([button])
        remaining -= 1
    return keyboard


def last_fm(http, profile, api_key):
    if 'lastfm' in profile:
        from plugins import lastfm
        lastfm.api_key = api_key
        last_track = lastfm.get_recently_played(http, profile['lastfm'], 1)
        if last_track and last_track[0]['now_playing']:
            last_track = last_track.pop()
            return last_track


def get_stats(tg):
    try:
        from plugins import chat_stats
    except AttributeError:
        return
    chat_id = tg.message['chat']['id']
    try:
        tg.database.query("SELECT COUNT(*) FROM `{}stats`;".format(chat_id))
    except _mysql_exceptions.ProgrammingError:
        return
    query = tg.database.store_result()
    chat_total = query.fetch_row()
    if chat_total[0][0] < 100:
        return
    tg.database.query("SELECT COUNT(*) FROM `{}stats` WHERE user_id={}".format(chat_id, user_id))
    query = tg.database.store_result()
    user_total = query.fetch_row()
    percentage = "{:.2%}".format(user_total[0][0] / chat_total[0][0])
    return {'user_total': user_total[0][0], 'percentage': percentage}


def add_entry(tg):
    try:
        with open('data/profile/{}.json'.format(user_id)) as file:
            profile = json.load(file)
    except (JSONDecodeError, FileNotFoundError):
        open('data/profile/{}.json'.format(user_id), 'w')
        profile = dict()
    site = tg.message['match'][1]
    user_name = tg.message['match'][2]
    for key, value in entries.items():
        if site.lower() == key or site.lower() in value['aliases']:
            if key in profile:
                message = "Updated your {}!".format(value['pretty_name'])
            else:
                message = "Successfully set your {}!".format(value['pretty_name'])
            profile.update({key: user_name})
            with open('data/profile/{}.json'.format(user_id), 'w') as file:
                json.dump(profile, file, sort_keys=True, indent=4)
            tg.send_message(message)
            return
    else:
        tg.send_message("This entry doesn't seem to be an option")


def delete_entry(tg):
    try:
        with open('data/profile/{}.json'.format(user_id)) as file:
            profile = json.load(file)
    except (JSONDecodeError, FileNotFoundError):
        tg.send_message(
            "You don't seem to have anything to delete :(\nAdd entries using <code>/profile website username</code>")
        return
    if tg.message['match'][1] == "del" or tg.message['match'][1] == "delete":
        site = tg.message['match'][2].lower()
    else:
        site = tg.message['match'][1].lower()
    for key, value in entries.items():
        if site.lower() == key or site.lower() in value['aliases']:
            try:
                del profile[key]
            except KeyError:
                tg.send_message("You haven't seemed to link a {}".format(value['pretty_name']))
                return
            tg.send_message("Successfully removed {}".format(value['pretty_name']))
            with open('data/profile/{}.json'.format(user_id), 'w') as file:
                json.dump(profile, file, sort_keys=True, indent=4)
            return
    tg.send_message("Invalid field")


def list_of_options():
    fields = list()
    with open('data/entries.json', 'r') as json_file:
        sites = json.load(json_file)
    for site in sites.values():
        fields.append(site['pretty_name'])
    return ", ".join(fields)


parameters = {
    'name': "Profile",
    'short_description': "Display information about yourself",
    'long_description': "The profile plugin allows you to share various details about yourself. You can add a field "
                        "using <code>/profile website username</code> You can also delete an entry using <code>/profile"
                        " delete website</code><b>List of fields:</b>\n{}".format(list_of_options()),
    'permissions': True
}

arguments = {
    'text': [
        "^/(profile|me)$",
        "^/(profile|me) (.*) (.*)$"
    ]
}

inline_arguments = [
    "^/?(profile|me)$"
]
