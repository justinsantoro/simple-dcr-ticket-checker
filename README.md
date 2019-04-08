# simple-dcr-ticket-checker

I wanted a simple way to be alerted when my tickets vote or expire without having to run a full node or use a VSPs email alert feature.
Yes, I can simply just check the explorer or my wallet every day, but why should I do that when I can have a script do it for me? :sunglasses:

Since funds are locked for an additional 256 blocks after a ticket votes or expires, it is only necessary
to check a ticket's status at most once every 18 - 20 hours.
If you are like me and shutdown and start up your computer at least once every 20 hours, simply running this script on
login is more than enough to ensure your funds are never sitting idle.

## Privacy

This script is intended to utilize a telegram bot you control to send notifications of your ticket events. While this is
not a perfectly private solution, IMO it's at least [better than receiving alerts from a VSP in your gmail inbox](https://www.reddit.com/r/decred/comments/7wzzbd/raqamiya_stakepool_added_email_notifications/du6d6e2/).

## Trust

Although in this specific case trust is not of huge concern, I feel it is necessary to mention that with any blockchain 
the only info you can 100% trust is that from your own (properly secured) full node. This script utilizes the
[dcrdata api](https://github.com/decred/dcrdata#dcrdata-api) at [dcrdata.org](https://dcrdata.org), therefore, you must trust that the information dcrdata.org provides is accurate.

## Setup

1. download and install [python3](https://www.python.org/downloads/) if not already installed. Python2.7 will most likely also work (I haven't tested it)
but is scheduled to be deprecated so Python3 is the way to go.
2. install required python packages: In a terminal type:
`pip install requests pyaml` If you have both python2 and python3 you may have to specify `pip3 install requests pyaml`
3. create a text file where you will list your active ticket txids ie `tickets.txt`
4. enter full path to `tickets.txt` file into `config.yml`
5. [create your telegram bot](https://core.telegram.org/bots#6-botfather) if not already done
6. copy telegram bot token into `config.yml`
7. enter the chat_id(s) you want to send notifications to into `config.yml`. To get your chat_id first, send a message
to your bot, then go to this link: `"https://api.telegram.org/bot{YOUR BOT TOKEN HERE}/getUpdates"`. The number labeled
"chat_id" ie `chat_id: 12345678` is the one you want.
8. update utc offset in `config.yml` to get fund maturity estimates in your timezone
9. set `checkTickets.py` to run automatically on startup or timed interval

Now all you need to do is enter new txids into your `tickets.txt` file as you purchase new tickets

You can verify the script is running by checking `log.txt` which will be generated in the same directory as `checkTickets.py`
