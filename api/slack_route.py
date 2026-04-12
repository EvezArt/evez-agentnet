#!/usr/bin/env python3
"""
/api/slack/route - EVEZ AgentNet Slack Integration
Handles Slack events and routes to appropriate systems.
n8n-compatible payloads for Linear/Asana import.
"""

import json
import hmac
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

class SlackRouteHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/api/slack/route':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data)

                # Process Slack event
                result = self.process_slack_event(payload)

                # Convert to n8n-compatible format for Linear/Asana
                n8n_payload = self.convert_to_n8n(payload, result)

                response = {
                    'status': 'processed',
                    'slack_event': payload.get('type'),
                    'routing_result': result,
                    'n8n_compatible': n8n_payload,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def process_slack_event(self, payload: dict) -> dict:
        """Process incoming Slack event."""
        event_type = payload.get('type')

        if event_type == 'message':
            text = payload.get('text', '')

            # Check for @vez mentions
            if '@vez' in text or '@EVEZ' in text:
                return {
                    'action': 'AGENT_TRIGGER',
                    'command': self.parse_command(text),
                    'priority': 'HIGH'
                }

            return {'action': 'LOG', 'priority': 'LOW'}

        elif event_type == 'reaction_added':
            return {'action': 'SENTIMENT_TRACK', 'priority': 'MEDIUM'}

        return {'action': 'IGNORE', 'priority': 'NONE'}

    def parse_command(self, text: str) -> dict:
        """Parse @vez commands."""
        text_lower = text.lower()

        if 'status' in text_lower:
            return {'type': 'STATUS_REQUEST'}
        elif 'spawn' in text_lower:
            return {'type': 'SPAWN_AGENT'}
        elif 'fire' in text_lower:
            return {'type': 'TRIGGER_FIRE'}
        else:
            return {'type': 'GENERAL_QUERY'}

    def convert_to_n8n(self, slack_payload: dict, result: dict) -> dict:
        """Convert Slack payload to n8n-compatible format."""
        return {
            'source': 'slack',
            'event_type': slack_payload.get('type'),
            'user': slack_payload.get('user'),
            'channel': slack_payload.get('channel'),
            'text': slack_payload.get('text'),
            'timestamp': slack_payload.get('ts'),
            'processed_action': result.get('action'),
            'priority': result.get('priority'),
            # n8n-specific fields
            'n8n_node': 'Slack Trigger',
            'workflow_compatible': True
        }

    def log_message(self, format, *args):
        pass

def run_server(port=8001):
    server = HTTPServer(('0.0.0.0', port), SlackRouteHandler)
    print(f"Slack route server running on port {port}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
