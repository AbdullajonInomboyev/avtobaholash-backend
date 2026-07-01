"""
WebSocket Consumers
- ExamConsumer: Talabaning imtihon sessiyasi (ekran blok, anti-cheat)
- MonitorConsumer: O'qituvchi real-time monitoring
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ExamConsumer(AsyncWebsocketConsumer):
    """Talaba imtihon sessiyasi"""

    async def connect(self):
        self.submission_id = self.scope['url_route']['kwargs']['submission_id']
        self.room_group = f'exam_{self.submission_id}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')

        if event_type == 'tab_switch':
            await self.handle_tab_switch(data)
        elif event_type == 'heartbeat':
            await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))

    async def handle_tab_switch(self, data):
        """Tab almashtirilganda — loglash va monitor ga xabar"""
        from .models import AntiCheatLog, AntiCheatEventType, AntiCheatSeverity, AssignmentSubmission
        submission = await database_sync_to_async(
            AssignmentSubmission.objects.get
        )(id=self.submission_id)

        submission.tab_switch_count += 1
        await database_sync_to_async(submission.save)()

        # Monitorga xabar
        await self.channel_layer.group_send(
            f'monitor_{submission.assignment_id}',
            {
                'type': 'student_alert',
                'student_id': str(submission.student_id),
                'event': 'tab_switch',
                'count': submission.tab_switch_count,
            }
        )

        # Chegara oshsa — bloklash
        from django.conf import settings
        max_switches = settings.ANTI_CHEAT.get('MAX_TAB_SWITCHES', 2)
        if submission.tab_switch_count >= max_switches:
            submission.is_locked = True
            submission.lock_reason = f'Tab {submission.tab_switch_count} marta almashtirildi'
            await database_sync_to_async(submission.save)()
            await self.send(text_data=json.dumps({
                'type': 'locked',
                'reason': submission.lock_reason,
            }))

    async def exam_message(self, event):
        await self.send(text_data=json.dumps(event))


class MonitorConsumer(AsyncWebsocketConsumer):
    """O'qituvchi — real-time monitoring"""

    async def connect(self):
        self.assignment_id = self.scope['url_route']['kwargs']['assignment_id']
        self.room_group = f'monitor_{self.assignment_id}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def student_alert(self, event):
        await self.send(text_data=json.dumps(event))
