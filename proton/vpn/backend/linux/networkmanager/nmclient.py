import gi
gi.require_version("NM", "1.0")
from gi.repository import NM, GLib


class NMClient:
    nm_client = NM.Client.new(None)
    main_loop = GLib.MainLoop()
    failure=None

    def _commit_changes_async(self, new_connection):
        new_connection.commit_changes_async(
            True,
            None,
            self.__dynamic_callback,
            dict(
                callback_type="commit",
                conn_name=new_connection.get_id(),
            )
        )
        self.main_loop.run()
        if NMClient.failure!=None:
            raise NMClient.failure

    def _add_connection_async(self, connection):
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
        self.main_loop.run()
        if NMClient.failure!=None:
            raise NMClient.failure

    def _start_connection_async(self, connection):
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
        self.main_loop.run()
        if NMClient.failure!=None:
            raise NMClient.failure

    def _remove_connection_async(self, connection):

        try:
            self.stop_connection_async(connection)
        except: # noqa
            pass

        connection.delete_async(
            None,
            self.__dynamic_callback,
            dict(
                callback_type="remove",
                conn_name=connection.get_id()
            )
        )
        self.main_loop.run()
        if NMClient.failure!=None:
            raise NMClient.failure

    def _stop_connection_async(self, connection):
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
        self.main_loop.run()
        if NMClient.failure!=None:
            raise NMClient.failure

    def __dynamic_callback(self, client, result, data):
        """Dynamic callback method.

        Args:
            client (NM.nm_client): nm client object
            result (Gio.AsyncResult): function
            data (dict): optional extra data
        """
        callback_type = data.get("callback_type")
        # conn_name = data.get("conn_name")
        try:
            callback_type_dict = dict(
                remove=dict(
                    finish_function=NM.Client.delete_finish,
                    msg="removed"
                )
            )
        except AttributeError:
            callback_type_dict = dict(
                add=dict(
                    finish_function=NM.Client.add_connection_finish,
                    msg="added"
                ),
                start=dict(
                    finish_function=NM.Client.activate_connection_finish,
                    msg="started"
                ),
                stop=dict(
                    finish_function=NM.Client.deactivate_connection_finish,
                    msg="stopped"
                ),
                commit=dict(
                    finish_function=NM.RemoteConnection.commit_changes_finish,
                    msg="commit"
                )
            )

        try:
            (callback_type_dict[callback_type]["finish_function"])(client, result)
            # msg = "The connection profile \"{}\" has been {}.".format(
            #     conn_name,
            #     callback_type_dict[callback_type]["msg"]
            # )
        except KeyError:
            pass
        except Exception as e:
            NMClient.failure=e

        self.main_loop.quit()
