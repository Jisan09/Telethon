from .common import EventBuilder, EventCommon, name_inner_event
from .. import utils
from ..tl import types, functions
from ..tl.custom.sendergetter import SenderGetter


@name_inner_event
class CallbackQuery(EventBuilder):
    """
    Represents a callback query event (when an inline button is clicked).
    """
    def build(self, update):
        if isinstance(update, types.UpdateBotCallbackQuery):
            event = CallbackQuery.Event(update)
        else:
            return

        event._entities = update._entities
        return self._filter_event(event)

    class Event(EventCommon, SenderGetter):
        """
        Represents the event of a new callback query.

        Members:
            query (:tl:`UpdateBotCallbackQuery`):
                The original :tl:`UpdateBotCallbackQuery`.
        """
        def __init__(self, query):
            super().__init__(chat_peer=query.peer, msg_id=query.msg_id)
            self.query = query
            self._sender_id = query.user_id
            self._input_sender = None
            self._sender = None
            self._message = None
            self._answered = False

        @property
        def id(self):
            """
            Returns the query ID. The user clicking the inline
            button is the one who generated this random ID.
            """
            return self.query.query_id

        @property
        def message_id(self):
            """
            Returns the message ID to which the clicked inline button belongs.
            """
            return self.query.msg_id

        @property
        def data(self):
            """
            Returns the data payload from the original inline button.
            """
            return self.query.data

        async def get_message(self):
            """
            Returns the message to which the clicked inline button belongs.
            """
            if self._message is not None:
                return self._message

            try:
                chat = await self.get_input_chat() if self.is_channel else None
                self._message = await self._client.get_messages(
                    chat, ids=self.query.msg_id)
            except ValueError:
                return

            return self._message

        async def _refetch_sender(self):
            self._sender = self._entities.get(self.sender_id)
            if not self._sender:
                return

            self._input_sender = utils.get_input_peer(self._chat)
            if not getattr(self._input_sender, 'access_hash', True):
                # getattr with True to handle the InputPeerSelf() case
                try:
                    self._input_sender = self._client.session.get_input_entity(
                        self._sender_id
                    )
                except ValueError:
                    m = await self.get_message()
                    if m:
                        self._sender = m._sender
                        self._input_sender = m._input_sender

        async def answer(
                self, message=None, cache_time=0, *, url=None, alert=False):
            """
            Answers the callback query (and stops the loading circle).

            Args:
                message (`str`, optional):
                    The toast message to show feedback to the user.

                cache_time (`int`, optional):
                    For how long this result should be cached on
                    the user's client. Defaults to 0 for no cache.

                url (`str`, optional):
                    The URL to be opened in the user's client. Note that
                    the only valid URLs are those of games your bot has,
                    or alternatively a 't.me/your_bot?start=xyz' parameter.

                alert (`bool`, optional):
                    Whether an alert (a pop-up dialog) should be used
                    instead of showing a toast. Defaults to ``False``.
            """
            if self._answered:
                return

            self._answered = True
            return await self._client(
                functions.messages.SetBotCallbackAnswerRequest(
                    query_id=self.query.query_id,
                    cache_time=cache_time,
                    alert=alert,
                    message=message,
                    url=url
                )
            )

        async def respond(self, *args, **kwargs):
            """
            Responds to the message (not as a reply). Shorthand for
            `telethon.telegram_client.TelegramClient.send_message` with
            ``entity`` already set.

            This method also creates a task to `answer` the callback.
            """
            self._client.loop.create_task(self.answer())
            return await self._client.send_message(
                await self.get_input_chat(), *args, **kwargs)

        async def reply(self, *args, **kwargs):
            """
            Replies to the message (as a reply). Shorthand for
            `telethon.telegram_client.TelegramClient.send_message` with
            both ``entity`` and ``reply_to`` already set.

            This method also creates a task to `answer` the callback.
            """
            self._client.loop.create_task(self.answer())
            kwargs['reply_to'] = self.query.msg_id
            return await self._client.send_message(
                await self.get_input_chat(), *args, **kwargs)

        async def edit(self, *args, **kwargs):
            """
            Edits the message iff it's outgoing. Shorthand for
            `telethon.telegram_client.TelegramClient.edit_message` with
            both ``entity`` and ``message`` already set.

            Returns the edited :tl:`Message`.

            This method also creates a task to `answer` the callback.
            """
            self._client.loop.create_task(self.answer())
            return await self._client.edit_message(
                await self.get_input_chat(), self.query.msg_id,
                *args, **kwargs
            )

        async def delete(self, *args, **kwargs):
            """
            Deletes the message. Shorthand for
            `telethon.telegram_client.TelegramClient.delete_messages` with
            ``entity`` and ``message_ids`` already set.

            If you need to delete more than one message at once, don't use
            this `delete` method. Use a
            `telethon.telegram_client.TelegramClient` instance directly.

            This method also creates a task to `answer` the callback.
            """
            self._client.loop.create_task(self.answer())
            return await self._client.delete_messages(
                await self.get_input_chat(), [self.query.msg_id],
                *args, **kwargs
            )
