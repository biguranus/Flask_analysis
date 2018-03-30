#!/usr/bin/python3
# -*- coding=utf-8 -*-


class _PackageBoundObject(object):

    def __init__(self, import_name, template_folder=None, root_path=None):
        #: The name of the package or module.  Do not change this once
        #: it was set by the constructor.
        self.import_name = import_name

        #: location of the templates.  ``None`` if templates should not be
        #: exposed.
        self.template_folder = template_folder

        if root_path is None:
            root_path = get_root_path(self.import_name)

        #: Where is the app root located?
        self.root_path = root_path

        self._static_folder = None
        self._static_url_path = None

    def _get_static_folder(self):
        if self._static_folder is not None:
            return os.path.join(self.root_path, self._static_folder)
    def _set_static_folder(self, value):
        self._static_folder = value
    static_folder = property(_get_static_folder, _set_static_folder, doc='''
    The absolute path to the configured static folder.
    ''')
    del _get_static_folder, _set_static_folder

    def _get_static_url_path(self):
        if self._static_url_path is not None:
            return self._static_url_path
        if self.static_folder is not None:
            return '/' + os.path.basename(self.static_folder)
    def _set_static_url_path(self, value):
        self._static_url_path = value
    static_url_path = property(_get_static_url_path, _set_static_url_path)
    del _get_static_url_path, _set_static_url_path

    @property
    def has_static_folder(self):
        """This is ``True`` if the package bound object's container has a
        folder for static files.

        .. versionadded:: 0.5
        """
        return self.static_folder is not None

    @locked_cached_property
    def jinja_loader(self):
        """The Jinja loader for this package bound object.

        .. versionadded:: 0.5
        """
        if self.template_folder is not None:
            return FileSystemLoader(os.path.join(self.root_path,
                                                 self.template_folder))

    def get_send_file_max_age(self, filename):
        """Provides default cache_timeout for the :func:`send_file` functions.

        By default, this function returns ``SEND_FILE_MAX_AGE_DEFAULT`` from
        the configuration of :data:`~flask.current_app`.

        Static file functions such as :func:`send_from_directory` use this
        function, and :func:`send_file` calls this function on
        :data:`~flask.current_app` when the given cache_timeout is ``None``. If a
        cache_timeout is given in :func:`send_file`, that timeout is used;
        otherwise, this method is called.

        This allows subclasses to change the behavior when sending files based
        on the filename.  For example, to set the cache timeout for .js files
        to 60 seconds::

            class MyFlask(flask.Flask):
                def get_send_file_max_age(self, name):
                    if name.lower().endswith('.js'):
                        return 60
                    return flask.Flask.get_send_file_max_age(self, name)

        .. versionadded:: 0.9
        """
        return total_seconds(current_app.send_file_max_age_default)

    def send_static_file(self, filename):
        """Function used internally to send static files from the static
        folder to the browser.

        .. versionadded:: 0.5
        """
        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')
        # Ensure get_send_file_max_age is called in all cases.
        # Here, we ensure get_send_file_max_age is called for Blueprints.
        cache_timeout = self.get_send_file_max_age(filename)
        return send_from_directory(self.static_folder, filename,
                                   cache_timeout=cache_timeout)

    def open_resource(self, resource, mode='rb'):
        """Opens a resource from the application's resource folder.  To see
        how this works, consider the following folder structure::

            /myapplication.py
            /schema.sql
            /static
                /style.css
            /templates
                /layout.html
                /index.html

        If you want to open the :file:`schema.sql` file you would do the
        following::

            with app.open_resource('schema.sql') as f:
                contents = f.read()
                do_something_with(contents)

        :param resource: the name of the resource.  To access resources within
                         subfolders use forward slashes as separator.
        :param mode: resource file opening mode, default is 'rb'.
        """
        if mode not in ('r', 'rb'):
            raise ValueError('Resources can only be opened for reading')
        return open(os.path.join(self.root_path, resource), mode)
