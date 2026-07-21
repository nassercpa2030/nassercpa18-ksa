import re
import time
from odoo import models, fields, api, _
import email
import email.policy
import imaplib
from datetime import date, datetime, timedelta
from ssl import SSLError
try:
    from xmlrpc.client import Binary as xmlrpclibBinary
except ImportError:
    import xmlrpclib
    xmlrpclibBinary = xmlrpclib.Binary if hasattr(xmlrpclib, 'Binary') else type(None)
from odoo.tools import html2plaintext

import logging
_logger = logging.getLogger(__name__)

class AiEmailMatrix(models.Model):
    _name = 'ai.email.matrix'
    _description = 'AI email matrix'
    _rec_name = 'agent_id'

    agent_id = fields.Many2one('copilot.agent.dashboard', string='Agent')
    vendor_id = fields.Many2one( "res.partner" ,string="Vendor")
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    average_score = fields.Float(string='Average Score')
    topics = fields.Char(string='Topics')
    query = fields.Char(string='Query')
    ai_email_matrix_line_ids = fields.One2many("ai.email.matrix.line", "ai_email_matrix_id", string="AI Email Matrix Lines")
    full_response = fields.Text(string='Full Response')


    def fetch_email_from_server(self, date_from, date_to, agent_id, vendor_id):
        main_start_date = date_from
        main_end_date = date_to

        records = self.env['ai.email.matrix'].search([
            ('agent_id', '=', agent_id),
            ('vendor_id', '=', vendor_id.id),
            ('date_from', '<=', main_end_date),
            ('date_to', '>=', main_start_date),
        ], order='date_from asc')

        covered = []
        uncovered = []

        cursor = main_start_date

        for rec in records:
            rec_start = max(rec.date_from, main_start_date)
            rec_end = min(rec.date_to, main_end_date)

            if cursor < rec_start:
                uncovered.append({
                    'date_from': cursor,
                    'date_to': rec_start - timedelta(days=1),
                })

            covered.append({
                'date_from': rec_start,
                'date_to': rec_end,
                'record_id': rec.id,
            })

            cursor = rec_end + timedelta(days=1)

        if cursor <= main_end_date:
            uncovered.append({
                'date_from': cursor,
                'date_to': main_end_date,
            })
        all_new_records = set()
        for item in uncovered:
            formatted_email, email_count = self.fetch_email_from_date_range(item['date_from'], item['date_to'] + timedelta(days=1), vendor_id)
            if email_count > 0:
                new_record = self.env['ai.email.matrix'].create({
                    'agent_id':agent_id,
                    'vendor_id':vendor_id.id,
                    'date_from': item['date_from'],
                    'date_to': item['date_to'],
                    'full_response': formatted_email
                })
                all_new_records.add(new_record)

        all_records = self.env['ai.email.matrix'].search([
            ('agent_id', '=', agent_id),
            ('vendor_id', '=', vendor_id.id),
            ('date_from', '<=', main_end_date),
            ('date_to', '>=', main_start_date),
        ], order='date_from asc')

        main_formatted_email = ""
        for rec in all_records:
            if not rec.ai_email_matrix_line_ids:
                all_new_records.add(rec)
            main_formatted_email += rec.full_response

        return main_formatted_email, list(all_new_records)


    def _get_relevant_mailboxes(self, imap_server):
        folders = {'inbox': 'INBOX', 'sent': None, 'all_mail': None}
        result, mailboxes = imap_server.list()
        if result != 'OK':
            return folders

        for raw_box in mailboxes:
            line = raw_box.decode('utf-8', errors='ignore')

            name_match = re.search(r'"([^"]+)"$', line)
            mailbox_name = name_match.group(1) if name_match else line.split()[-1]

            line_lower = line.lower()
            name_lower = mailbox_name.lower()

            if '\\all' in line_lower or 'all mail' in name_lower:
                folders['all_mail'] = mailbox_name
            elif '\\sent' in line_lower or 'sent' in name_lower:
                folders['sent'] = mailbox_name
            elif 'inbox' in name_lower:
                folders['inbox'] = mailbox_name

        return folders


    def format_email_text(self, msg_dict, is_outgoing=False):
        role = "Responder" if is_outgoing else "Sender"
        sender = msg_dict.get('email_from') or msg_dict.get('from') or ''
        date_str = msg_dict.get('date')
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except Exception:
            formatted_date = date_str or ''

        body_html = msg_dict.get('body') or ''
        body_text = html2plaintext(body_html).strip()

        formatted_text = (
            f"{role}: {sender}\n"
            f"Date: {formatted_date}\n\n"
            f"Mail Body:\n"
            f"{body_text}\n\n"
        )

        return formatted_text

    def safe_select_mailbox(self, imap_server, mailbox_name):
        try:
            # Wrap in double quotes to handle spaces like [Gmail]/All Mail
            quoted_name = f'"{mailbox_name}"'
            status, data = imap_server.select(quoted_name)
            return status == 'OK'
        except Exception as e:
            _logger.error("Failed to select mailbox %s: %s", mailbox_name, e)
            return False

    def fetch_email_from_date_range(self, start_date=None, end_date=None, vendor_id=None):
        start_time = time.time()
        MailThread = self.env['mail.thread']
        all_email_server = self.env['user.email.credentials'].search([('server_type','=','incoming'),('user_smtp_status','=','connected')])
        formatted_email = ""
        email_count = 0
        for item in all_email_server:
            today = date.today()
            yesterday = today - timedelta(days=1)

            from_date_str = start_date.strftime("%d-%b-%Y") if start_date else yesterday.strftime("%d-%b-%Y")
            to_date_str = end_date.strftime("%d-%b-%Y") if end_date else today.strftime("%d-%b-%Y")

            server_obj = self.env['fetchmail.server'].new({
                'name': 'Temporary IMAP Server',
                'server': item.server,
                'port': item.port,
                'user': item.user,
                'password': item.password,
                'is_ssl': item.is_ssl,
            })
            server = server_obj
            imap_query = (
                f'(SINCE "{from_date_str}" BEFORE "{to_date_str}" '
                f'TEXT "{vendor_id.complete_name}")'
            )

            email_query = f'({imap_query})'

            _logger.info("Fetching emails from server: %s using query: %s", server.name, email_query)
            imap_server = None

            connection_type = server._get_connection_type()

            if connection_type == 'imap':
                try:
                    imap_server = server.connect()

                    folders = self._get_relevant_mailboxes(imap_server)

                    if folders['all_mail']:
                        mailboxes = [folders['all_mail']]
                    else:
                        mailboxes = [
                            box for box in (folders['inbox'], folders['sent']) if box
                        ]

                    for mailbox_name in mailboxes:

                        mailbox_selected = self.safe_select_mailbox(imap_server, mailbox_name)
                        if not mailbox_selected:
                            continue

                        mailbox_selected = True

                        result, data = imap_server.search(None, email_query)
                        if result != 'OK':
                            continue

                        email_ids = data[0].split()
                        if not email_ids:
                            continue

                        all_email_ids = b','.join(email_ids)
                        result, msg_data = imap_server.fetch(all_email_ids, b'(RFC822)')
                        if result != 'OK':
                            continue

                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                message = response_part[1]
                                if isinstance(message, xmlrpclibBinary):
                                    message = bytes(message.data)
                                if isinstance(message, str):
                                    message = message.encode('utf-8')
                                msg_obj = email.message_from_bytes(message, policy=email.policy.SMTP)
                                msg_dict = MailThread.message_parse(msg_obj, save_original=False)
                                formatted_email += self.format_email_text(
                                    msg_dict,
                                    is_outgoing=(item.user.lower() in (msg_dict.get('email_from') or '').lower())
                                )
                                email_count +=1

                except imaplib.IMAP4.error as e:
                    _logger.error("IMAP Error for server %s: %s", server.name, e)
                except SSLError as e:
                    _logger.error("SSL Error for server %s: %s", server.name, e)
                except Exception as e:
                    _logger.error("Unexpected Error while fetching emails from server %s: %s", server.name, e)
                finally:
                    if imap_server:
                        try:
                            if mailbox_selected:
                                imap_server.close()  # only if SELECT succeeded
                        except Exception:
                            pass
                        finally:
                            imap_server.logout()
        end_time = time.time()
        print(f"For {email_count} Emails, Execution time is: {end_time - start_time:.6f} seconds")
        return formatted_email, email_count


