import logging
from concurrent.futures import Future
from threading import Thread
from typing import Callable, Optional

import gi
gi.require_version("NM", "1.0")  # noqa: required before importing NM module
from gi.repository import NM, GLib

from proton.vpn.connection.exceptions import VPNConnectionError

logger = logging.getLogger(__name__)


class NMClient:
    def __init__(self):
        self._main_loop = GLib.MainLoop()
        # Setting daemon=True when creating the thread makes that this thread
        # exits abruptly when the python process exits. It would be better to
        # exit the thread running the main loop calling self._main_loop.quit().
        Thread(target=self._main_loop.run, daemon=True).start()

        callback, future = self.create_nmcli_callback(
            finish_method_name="new_finish"
        )
        NM.Client().new_async(None, callback, None)
        self.nm_client = future.result()

    def create_nmcli_callback(self, finish_method_name: str) -> (Callable, Future):
        future = Future()
        future.set_running_or_notify_cancel()

        def callback(source_object, res, userdata):
            try:
                # On errors, according to the docs, the callback can be called
                # with source_object/res set to None.
                # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_async
                if not source_object or not res:

                    raise VPNConnectionError(
                        f"An unexpected error occurred initializing NMClient: "
                        f"source_object = {source_object}, res = {res}."
                    )

                result = getattr(source_object, finish_method_name)(res)

                # According to the docs, None is returned on errors
                # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_finish
                if not result:
                    raise VPNConnectionError(
                        "An unexpected error occurred initializing NMCLient"
                    )

                future.set_result(result)
            except BaseException as e:
                future.set_exception(e)

        return callback, future

    def _commit_changes_async(
            self, new_connection: NM.RemoteConnection
    ) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="commit_changes_finish"
        )
        new_connection.commit_changes_async(
            True,
            None,
            callback,
            None
        )
        return future

    def _add_connection_async(self, connection: NM.Connection) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="add_connection_finish"
        )
        self.nm_client.add_connection_async(
            connection,
            True,
            None,
            callback,
            None
        )
        return future

    def _start_connection_async(self, connection: NM.Connection) -> Future:
        """Start ProtonVPN connection."""
        callback, future = self.create_nmcli_callback(
            finish_method_name="activate_connection_finish"
        )
        self.nm_client.activate_connection_async(
            connection,
            None,
            None,
            None,
            callback,
            None
        )
        return future

    def _remove_connection_async(
            self, connection: NM.RemoteConnection
    ) -> Future:
        callback, future = self.create_nmcli_callback(
            finish_method_name="delete_finish"
        )
        connection.delete_async(
            None,
            callback,
            None
        )
        return future

    def get_active_connection(self, uuid: str) -> Optional[NM.ActiveConnection]:
        active_connections = self.nm_client.get_active_connections()

        for connection in active_connections:
            if connection.get_uuid() == uuid:
                return connection

        return None

    def get_connection(self, uuid: str) -> Optional[NM.RemoteConnection]:
        return self.nm_client.get_connection_by_uuid(uuid)

    def release_resources(self):
        self._main_loop.quit()
