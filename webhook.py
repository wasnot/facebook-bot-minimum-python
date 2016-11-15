#!/usr/bin/env python
import logging
import json
import base64

import webapp2
from google.appengine.api import urlfetch

from secret import PAGE_ACCESS_TOKEN, VERIFY_TOKEN


class WebHookHandler(webapp2.RequestHandler):
    def get(self):
        logging.info(str(self.request))
        if self.request.get('hub.mode') == 'subscribe' and self.request.get('hub.verify_token') == VERIFY_TOKEN:
            logging.info('Validating webhook')
            self.response.status = 200
            self.response.write(self.request.get('hub.challenge'))
        else:
            logging.error("Failed validation. Make sure the validation tokens match.")
            self.error(403)

    def post(self):
        logging.info('request:' + str(self.request))
        data = json.loads(self.request.body)
        logging.info(data)

        # Make sure this is a page subscription
        if data['object'] == 'page':
            # Iterate over each entry - there may be multiple if batched
            for entry in data['entry']:
                page_id = entry['id']
                time_of_event = entry['time']
                logging.info('pageID:{}, timeOfEvent:{}'.format(page_id, time_of_event))
                logging.info('entry:{}'.format(entry))

                # Iterate over each messaging event
                for event in entry['messaging']:
                    logging.info('event:{}'.format(event))
                    if event.get('message'):
                        self.receive_message(event)
                    elif event.get('postback'):
                        self.received_postback(event)
                    elif event.get('account_linking'):
                        self.received_account_linking(event)
                    else:
                        logging.info("Webhook received unknown event: " + str(event))

            # Assume all went well.
            #
            # You must send back a 200, within 20 seconds, to let us know
            # you've successfully received the callback. Otherwise, the request
            # will time out and we will keep trying to resend.
            self.response.status = 200

    def receive_message(self, event):
        # Putting a stub for now, we'll expand it in the following steps
        logging.info("Message data: {}".format(event['message']))
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        time_of_message = event['timestamp']
        message = event['message']

        logging.info("Received message for user {} and page {} at {} with message:".format(
            sender_id, recipient_id, time_of_message))
        logging.info(json.dumps(message))

        message_id = message['mid']

        message_text = message.get('text')
        message_attachments = message.get('attachments')

        if message_text:
            # If we receive a text message, check to see if it matches a keyword
            # and send back the example.Otherwise, just echo the text we received.
            if message_text == 'generic':
                self.send_generic_message(sender_id)
            elif message_text == 'login':
                self.send_login_button(sender_id)
            elif message_text == 'logout':
                self.send_logout_button(sender_id)
            else:
                self.send_text_message(sender_id, message_text)

        elif message_attachments:
            self.send_text_message(sender_id, "Message with attachment received")

    def received_postback(self, event):
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        time_of_postback = event['timestamp']

        # The 'payload' param is a developer-defined field which is set in a postback
        # button for Structured Messages.
        payload = event['postback']['payload']

        logging.info("Received postback for user {} and page {} with payload '{}' at {}".format(
            sender_id, recipient_id, payload, time_of_postback))

        # When a postback is called, we'll send a message back to the sender to
        # let them know it was successful
        self.send_text_message(sender_id, "Postback called")

    def received_account_linking(self, event):
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        time_of_postback = event['timestamp']

        status = event['account_linking']['status']
        authorization_code = event['account_linking'].get('authorization_code')

        logging.info("Received account linking for user {} and page {} with status '{}' at {}".format(
            sender_id, recipient_id, status, time_of_postback))
        logging.info('authorization_code: {}'.format(authorization_code))
        if authorization_code:
            code = authorization_code.split('.')

            uuid = None
            if len(code) == 3:
                input = bytes(code[1])
                rem = len(input) % 4
                if rem > 0:
                    input += b'=' * (4 - rem)
                js = base64.urlsafe_b64decode(input)
                logging.info(js)
                uuid = json.loads(js).get('sub')

            self.send_text_message(sender_id, "AccountLinking called: {}, {}".format(status, uuid))
        else:
            self.send_text_message(sender_id, "AccountLinking called: {}".format(status))

    def send_generic_message(self, recipient_id):
        messageData = {
            'recipient': {
                'id': recipient_id
            },
            'message': {
                'attachment': {
                    'type': "template",
                    'payload': {
                        'template_type': "generic",
                        'elements': [{
                            'title': "rift",
                            'subtitle': "Next-generation virtual reality",
                            'item_url': "https://www.oculus.com/en-us/rift/",
                            'image_url': "http://messengerdemo.parseapp.com/img/rift.png",
                            'buttons': [{
                                'type': "web_url",
                                'url': "https://www.oculus.com/en-us/rift/",
                                'title': "Open Web URL"
                            }, {
                                'type': "postback",
                                'title': "Call Postback",
                                'payload': "Payload for first bubble",
                            }],
                        }, {
                            'title': "touch",
                            'subtitle': "Your Hands, Now in VR",
                            'item_url': "https://www.oculus.com/en-us/touch/",
                            'image_url': "http://messengerdemo.parseapp.com/img/touch.png",
                            'buttons': [{
                                'type': "web_url",
                                'url': "https://www.oculus.com/en-us/touch/",
                                'title': "Open Web URL"
                            }, {
                                'type': "postback",
                                'title': "Call Postback",
                                'payload': "Payload for second bubble",
                            }]
                        }]
                    }
                }
            }
        }

        self.call_send_api(messageData)

    def send_login_button(self, recipient_id):
        messageData = {
            'recipient': {
                'id': recipient_id
            },
            'message': {
                'attachment': {
                    'type': "template",
                    'payload': {
                        'template_type': "generic",
                        'elements': [{
                            'title': "Welcome to SENSY-ID",
                            'subtitle': "Next-generation virtual reality",
                            'image_url': "http://messengerdemo.parseapp.com/img/rift.png",
                            'buttons': [{
                                'type': "account_link",
                                'url': "https://id.sensy.jp/authorize",
                                # 'url': "http://localhost:11080/authorize",
                            }],
                        }]
                    }
                }
            }
        }

        self.call_send_api(messageData)

    def send_logout_button(self, recipient_id):
        messageData = {
            'recipient': {
                'id': recipient_id
            },
            'message': {
                'attachment': {
                    'type': "template",
                    'payload': {
                        'template_type': "generic",
                        'elements': [{
                            'title': "Welcome to SENSY-ID",
                            'subtitle': "Next-generation virtual reality",
                            'image_url': "http://messengerdemo.parseapp.com/img/rift.png",
                            'buttons': [{
                                'type': "account_unlink"
                            }],
                        }]
                    }
                }
            }
        }

        self.call_send_api(messageData)

    def send_text_message(self, recipient_id, message_text):
        message_data = {
            'recipient': {
                'id': recipient_id
            },
            'message': {
                'text': message_text
            }
        }

        self.call_send_api(message_data)

    @staticmethod
    def call_send_api(message_data):
        try:
            result = urlfetch.fetch(
                url='https://graph.facebook.com/v2.6/me/messages?access_token={}'.format(PAGE_ACCESS_TOKEN),
                method=urlfetch.POST,
                payload=json.dumps(message_data),
                headers={'Content-Type': 'application/json'}
                )
            if result.status_code == 200:
                body = json.loads(result.content)
                recipient_id = body['recipient_id']
                message_id = body['message_id']

                logging.info("Successfully sent generic message with id {} to recipient {}".format(
                    message_id, recipient_id))
            else:
                logging.error("Unable to send message.")
                logging.error(result.content)
        except Exception as error:
            logging.error("Unable to send message.")
            logging.error(error)
