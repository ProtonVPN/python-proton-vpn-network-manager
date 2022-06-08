import logging
from concurrent.futures import Future
from threading import Thread
from typing import Callable

import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, GLib


logger = logging.getLogger(__name__)


class NMClient:
    nm_client = None

    def __init__(self):
        self._main_loop = GLib.MainLoop()
        # Setting daemon=True when creating the thread makes that this thread exits abruptly when the python
        # process exits. It would be better to exit the thread running the main loop calling self._main_loop.quit().
        Thread(target=self._main_loop.run, daemon=True).start()

        callback, future = self.create_nmcli_callback(finish_method_name="new_finish")
        NM.Client().new_async(None, callback, None)
        self.nm_client = future.result()

    def create_nmcli_callback(self, finish_method_name: str) -> (Callable, Future):
        future = Future()
        future.set_running_or_notify_cancel()

        def callback(source_object, res, userdata):
            try:
                if not source_object or not res:
                    # On errors, according to the docs, the callback can be called with source_object/res set to None
                    # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_async
                    raise Exception(f"An unexpected error occurred initializing NMClient: "
                                    f"source_object = {source_object}, res = {res}.")

                result = getattr(source_object, finish_method_name)(res)

                if not result:
                    # According to the docs, None is returned when there was ane error
                    # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_finish
                    raise Exception("An unexpected error occurred initializing NMCLient")

                future.set_result(result)
            except BaseException as e:
                future.set_exception(e)

        return callback, future

    def _commit_changes_async(self, new_connection: "NM.RemoteConnection") -> Future:
        callback, future = self.create_nmcli_callback(finish_method_name="commit_changes_finish")
        new_connection.commit_changes_async(
            True,
            None,
            callback,
            None
        )
        return future

    def _add_connection_async(self, connection: "NM.Connection") -> Future:
        callback, future = self.create_nmcli_callback(finish_method_name="add_connection_finish")
        self.nm_client.add_connection_async(
            connection,
            True,
            None,
            callback,
            None
        )
        return future

    def _start_connection_async(self, connection: "NM.Connection") -> Future:
        """Start ProtonVPN connection."""
        callback, future = self.create_nmcli_callback(finish_method_name="activate_connection_finish")
        self.nm_client.activate_connection_async(
            connection,
            None,
            None,
            None,
            callback,
            None
        )
        return future

    def _remove_connection_async(self, connection: "NM.RemoteConnection") -> Future:
        callback, future = self.create_nmcli_callback(finish_method_name="delete_finish")
        connection.delete_async(
            None,
            callback,
            None
        )
        return future

    def _stop_connection_async(self, connection: "NM.ActiveConnection") -> Future:
        """Stop ProtonVPN connection.

        Args(optional):
            client (NM.nm_client): new NetworkManager Client object
        """
        callback, future = self.create_nmcli_callback(finish_method_name="deactivate_connection_finish")
        self.nm_client.deactivate_connection_async(
            connection,
            None,
            callback,
            None
        )
        return future

    def release_resources(self):
        self._main_loop.quit()
