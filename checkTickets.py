#!/usr/bin/env python3

import os
import datetime
import requests
import yaml

script_path = os.path.dirname(os.path.realpath(__file__))
dcrdata_api_url = "https://dcrdata.org/api/"
dcrdata_api_tinfo = dcrdata_api_url + "tx/{}/tinfo"
dcrdata_api_best = dcrdata_api_url + "block/best"
telegrambot_api_url = "https://api.telegram.org/bot{}/{}"
log_path = script_path + "/log.txt"
config_path = script_path + "/config.yml"
config = None


def log(message):
    now = datetime.datetime.utcnow()
    with open(log_path, 'a') as f:
        f.write(str(now.date()) + " - " + str(now.time()) + ": " + message + "\n")


def get_ticket_ids(file_path):
    with open(file_path, 'r') as ticket_ids:
        return [line.rstrip('\n').rstrip('\r') for line in ticket_ids]


def check_ticket(ticket_id):
    pre_vote = ['immature', 'live']
    try:
        r = requests.get(dcrdata_api_tinfo.format(ticket_id))
        r.raise_for_status()
        tx = r.json()
        log("checked ticket " + ticket_id)
        if tx['status'] not in pre_vote:
            return tx
        else:
            return None
    except Exception as e:
        print(e)


def get_event_block_height(tx):
    if tx['status'] == 'voted' or tx['status'] == 'missed':
        return int(tx['lottery_block']['height'])
    if tx['status'] == 'expired':
        return int(tx['expiration_height'])


def get_current_block_height():
    try:
        r = requests.get(dcrdata_api_best)
        r.raise_for_status()
        return int(r.json()['height'])
    except Exception as e:
        print(e)


def get_funds_release_time(tx, utc_offset):
    immature_block_length = 256
    block_time = 5  # minutes
    event_block_height = get_event_block_height(tx)
    current_block_height = get_current_block_height()
    blocks_to_go = immature_block_length - (current_block_height - event_block_height)
    mature_utc = datetime.datetime.utcnow() + datetime.timedelta(minutes=blocks_to_go*block_time)
    mature_timezone = mature_utc + datetime.timedelta(hours=int(utc_offset))
    return mature_timezone.strftime('%A %B %d, around %I:%M%p')


def get_caption(tx):
    return """Ticket {}!
            Funds will be available on {}.
            """.format(tx['status'], get_funds_release_time(tx, config['utc_offset']))


def notify(bot_token, chat_ids, tx):
    command = 'sendMessage'
    payload = {'text': get_caption(tx)}
    if type(chat_ids).__name__ != 'list':
        chat_ids = [chat_ids]
    for chat in chat_ids:
        payload['chat_id'] = chat
        try:
            r = requests.get(telegrambot_api_url.format(bot_token, command), params=payload)
            r.raise_for_status()
            log('sent notification to telid: ' + str(chat))
        except Exception as e:
            print(e)


def parse_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.load(f, Loader=yaml.BaseLoader)


def write_active_tickets(file_path, tickets):
    with open(file_path, 'w') as f:
        f.write(tickets)


def main():
    global config
    config = parse_config(config_path)
    ticket_ids = get_ticket_ids(config['tickets_file_path'])

    if ticket_ids:
        active_tickets = ''
        for ticket in ticket_ids:
            tx = check_ticket(ticket)
            # if ticket voted, missed, or expired send notification
            if tx:
                notify(config['bot_token'], config['tel_chat_ids'], tx)
            else:
                # append ticket to list to be checked again later
                active_tickets += (ticket + '\n')
        if active_tickets:
            # re-write active tickets into file
            write_active_tickets(config['tickets_file_path'], active_tickets)
            log('rewrote active tickets')
        else:
            # if no more active tickets overwrite with empty file
            open(config['tickets_file_path'], 'w').close()
            log('rewrote empty file')


if __name__ == '__main__':
    log('running...')
    main()
