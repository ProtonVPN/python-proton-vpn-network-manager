import logging
from concurrent.futures import Future
from threading import Thread
from typing import Callable

import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, GLib

from proton.vpn.connection.exceptions import VPNConnectionError

logger = logging.getLogger(__name__)


class NMClient:
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
                    raise VPNConnectionError(f"An unexpected error occurred initializing NMClient: "
                                             f"source_object = {source_object}, res = {res}.")

                result = getattr(source_object, finish_method_name)(res)

                if not result:
                    # According to the docs, None is returned when there was ane error
                    # https://lazka.github.io/pgi-docs/index.html#NM-1.0/classes/Client.html#NM.Client.new_finish
                    raise VPNConnectionError("An unexpected error occurred initializing NMCLient")

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

    def get_connection(self, uuid=str):
        # Gets all active connections
        active_conn_list = self.nm_client.get_active_connections()
        # Gets all non-active stored connections
        non_active_conn_list = self.nm_client.get_connections()

        # The reason for having this difference is because NM can
        # have active connections that are not stored. If such
        # connection is stopped/disabled then it is removed from
        # NM, and thus the distinction between active and "regular" connections.

        all_conn_list = active_conn_list + non_active_conn_list

        for conn in all_conn_list:
            # Since a connection can be removed at any point, an AttributeError try/catch
            # has to be performed, to ensure that a connection that existed previously when
            # doing the `if` statement was not removed.
            try:
                if (
                        conn.get_connection_type().lower() != "vpn"
                        and conn.get_connection_type().lower() != "wireguard"
                ):
                    continue

                # If it's an active connection then we attempt to get
                # its stored connection. If an AttributeError is raised
                # then it means that the conneciton is a stored connection
                # and not an active connection, and thus the exception
                # can be safely ignored.
                try:
                    conn = conn.get_connection()
                except AttributeError:
                    pass

                if conn.get_uuid() == uuid:
                    return conn
            except AttributeError:
                pass

        return None

    def release_resources(self):
        self._main_loop.quit()
