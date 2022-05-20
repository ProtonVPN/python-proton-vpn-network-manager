import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, GLib


class NMClient:
    nm_client = None

    def __init__(self):
        self.result = False
        self._main_loop = GLib.MainLoop()
        self.failure = None

        _nm_client = NM.Client()
        _nm_client.new_async(None, self.cb, None)

        while not self.result:
            _nm_client.get_main_context().iteration(may_block=True)

    def cb(self, source_object, res, userdata):
        self.result = True
        self.nm_client = source_object.new_finish(res)

    def _commit_changes_async(self, new_connection: "NM.RemoteConnection"):
        new_connection.commit_changes_async(
            True,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="commit",
                conn_name=new_connection.get_id(),
            )
        )
        self._main_loop.run()
        if self.failure is not None:
            raise self.failure

    def _add_connection_async(self, connection: "NM.Connection"):
        self.nm_client.add_connection_async(
            connection,
            True,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="add",
                conn_name=connection.get_id(),
            )
        )
        self._main_loop.run()
        if self.failure is not None:
            raise self.failure

    def _start_connection_async(self, connection: "NM.Connection"):
        """Start ProtonVPN connection."""
        self.nm_client.activate_connection_async(
            connection,
            None,
            None,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="start",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if self.failure is not None:
            raise self.failure

    def _remove_connection_async(self, connection: "NM.RemoteConnection"):
        connection.delete_async(
            None,
            self.__dynamic_callback,
            dict(
                callback_type="remove",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if self.failure is not None:
            raise self.failure

    def _stop_connection_async(self, connection: "NM.ActiveConnection"):
        """Stop ProtonVPN connection.

        Args(optional):
            client (NM.nm_client): new NetworkManager Client object
        """
        self.nm_client.deactivate_connection_async(
            connection,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="stop",
                conn_name=connection.get_id()
            )
        )
        self._main_loop.run()
        if self.failure is not None:
            raise self.failure

    def __dynamic_callback(self, client, result, data):
        """Dynamic callback method.

        Args:
            client (NM.nm_client): nm client object
            result (Gio.AsyncResult): function
            data (dict): optional extra data
        """
        callback_type = data.get("callback_type")
        try:
            callback_type_dict = dict(
                remove=dict(
                    finish_function=NM.Client.delete_finish,
                    msg="remove"
                )
            )
        except AttributeError:
            callback_type_dict = dict(
                add=dict(
                    finish_function=NM.Client.add_connection_finish
                ),
                start=dict(
                    finish_function=NM.Client.activate_connection_finish
                ),
                stop=dict(
                    finish_function=NM.Client.deactivate_connection_finish
                ),
                commit=dict(
                    finish_function=NM.RemoteConnection.commit_changes_finish
                )
            )

        try:
            callback_type_dict[
                callback_type
            ]["finish_function"](client, result)
        except KeyError:
            pass
        except Exception as e:
            self.failure = e

        self._main_loop.quit()
