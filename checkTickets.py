#!/usr/bin/env python3

import os
import datetime
import io
import traceback
import sys
import requests
import yaml
import json


dcrdata_api_url = "https://dcrdata.org/api/"
dcrdata_api_tinfo = dcrdata_api_url + "tx/{}/tinfo"
dcrdata_api_best = dcrdata_api_url + "block/best"
pi_api_url = "https://proposals.decred.org/api/v1/proposals/activevote"
telegrambot_api_url = "https://api.telegram.org/bot{}/{}"

script_path = os.path.dirname(os.path.realpath(__file__))
log_path = script_path + "/log.txt"
config_path = script_path + "/config.yml"
checked_votes_path = script_path + '/checked_votes.txt'
to_delete = script_path + '/to_delete.txt'
config = None


def log(message):
    now = datetime.datetime.utcnow()
    with open(log_path, 'a') as f:
        f.write(str(now.date()) + " - " + str(now.time()) + ": " + message + "\n")


def _get_traceback_string(ex_type, ex, tb):
    output = io.StringIO()
    traceback.print_exception(ex_type, ex, tb, file=output)
    return output.getvalue()


def log_unexpected(etype, value, tb):
    log("\n" + _get_traceback_string(etype, value, tb)[:-1])


def read_file(file_path):
    with open(file_path, 'r') as f:
        return [line.rstrip('\n').rstrip('\r') for line in f]


def get_active_votes():
    r = requests.get(pi_api_url)
    if r.status_code != 200:
        log('get_active_votes(): ' + r.text)
        return []
    else:
        votes = r.json()['votes']
        log('got {} active votes'.format(len(votes)))
        return votes


def get_ticket(ticket_id):
    r = requests.get(dcrdata_api_tinfo.format(ticket_id))
    if r.status_code != 200:
        log('check_ticket(): ' + r.text)
        return None
    else:
        tx = r.json()
        log("checked ticket " + ticket_id)
        return tx


def get_event_block_height(tx):
    if tx['status'] == 'voted' or tx['status'] == 'missed':
        return int(tx['lottery_block']['height'])
    if tx['status'] == 'expired':
        return int(tx['expiration_height'])


def get_current_block_height():
    r = requests.get(dcrdata_api_best)
    if r.status_code != 200:
        log('get_current_block_height(): ' + r.text)
        return 0
    return int(r.json()['height'])


def get_funds_release_time(tx, utc_offset):
    immature_block_length = 256
    block_time = 5  # minutes
    event_block_height = get_event_block_height(tx)
    current_block_height = get_current_block_height()
    blocks_to_go = immature_block_length - (current_block_height - event_block_height)
    mature_utc = datetime.datetime.utcnow() + datetime.timedelta(minutes=blocks_to_go*block_time)
    mature_timezone = mature_utc + datetime.timedelta(hours=int(utc_offset))
    return mature_timezone.strftime('%A %B %d, around %I:%M%p')


def short_id(txid):
    return txid[:4] + '...' + txid[-4:]


def eligible_to_vote_message(eligible, vote):
    return '<b>{}</b> Tickets now eligible to vote on proposal: ' \
           '<a href="https://proposals.decred.org/proposals/{}">{}</a>\n'.format(eligible,
                                                                                 vote['startvote']['vote']['token'],
                                                                                 vote['proposal']['name'])


def ticket_event_message(tx, txid):
    return "Ticket <code>{}</code> <b>{}</b>! Funds will be available on <i>{}</i>.\n".format(short_id(txid),
                                                                  tx['status'],
                                                                  get_funds_release_time(tx, config['utc_offset']))


def notify(bot_token, chat_ids, ticket_message, vote_message):
    command = 'sendMessage'
    if vote_message and ticket_message:
        text = '{} \n\n {}'.format(ticket_message, vote_message)
    elif vote_message:
        text = vote_message
    else:
        text = ticket_message
    payload = {'text': text, 'parse_mode': 'HTML'}
    if type(chat_ids).__name__ != 'list':
        chat_ids = [chat_ids]

    sent_messages = ''
    for chat in chat_ids:
        payload['chat_id'] = chat
        r = requests.get(telegrambot_api_url.format(bot_token, command), params=payload)
        print(r.url)
        if r.status_code != 200:
            log('notify(): ' + r.text)
        else:
            log('sent notification to telid: ' + str(chat))
            sent_messages += json.dumps({"message_id": r.json()['message_id'], "chat_id": chat}) + "\n"

    write_file(to_delete, sent_messages)


def parse_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.load(f, Loader=yaml.BaseLoader)


def write_file(file_path, lines):
    with open(file_path, 'w') as f:
        f.write(lines)


def check_tickets(ticket_ids):
    message = ''
    pre_vote = ['immature', 'live']
    active_tickets = ''
    for ticket in ticket_ids:
        tx = get_ticket(ticket)
        if tx:
            if tx['status'] in pre_vote:
                active_tickets += ticket + '\n'
            else:
                message += ticket_event_message(tx, ticket)
        else:
            active_tickets += ticket + '\n'
    write_file(config['tickets_file_path'], active_tickets)
    log('wrote active tickets file ' + config['tickets_file_path'])
    return message


def check_active_votes(ticket_ids):
    message = ''
    checked_votes = read_file(checked_votes_path) if os.path.exists(checked_votes_path) else []
    active_votes = get_active_votes()
    active_votes_s = ''
    for vote in active_votes:
        token = vote['startvote']['vote']['token']
        active_votes_s += token + '\n'
        if token not in checked_votes:
            eligible = 0
            for ticket in ticket_ids:
                if ticket in vote['startvotereply']['eligibletickets']:
                    eligible += 1
            if eligible:
                message += eligible_to_vote_message(eligible, vote)
    write_file(checked_votes_path, active_votes_s)
    log('wrote active votes file ' + checked_votes_path)
    return message


def delete_old(bot_token):
    command = 'deleteMessage'
    if os.path.exists(to_delete):
        messages = read_file(to_delete)
        for message in messages:
            r = requests.get(telegrambot_api_url.format(bot_token, command), params=json.loads(message))
            print(r.url)
            if r.status_code != 200:
                log('notify(): ' + r.text)
            else:
                log('deleted old message: ' + message)


def main():
    global config
    config = parse_config(config_path)

    if config['delete_old']:
        delete_old(config['bot_token'])

    ticket_ids = read_file(config['tickets_file_path'])
    if ticket_ids:
        vote_message = None
        ticket_message = check_tickets(ticket_ids)
        if config['vote_eligibility']:
            vote_message = check_active_votes(ticket_ids)
        if ticket_message or vote_message:
            notify(config['bot_token'], config['chat_ids'], ticket_message, vote_message)
    else:
        log('no tickets to check')


if __name__ == '__main__':
    sys.excepthook = log_unexpected
    log('running...')
    main()
