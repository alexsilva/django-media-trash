# coding: utf-8
# source taken from:
# https://github.com/sehmaschine/django-filebrowser
# ====================

import datetime
import mimetypes
import os
import tempfile
import time

from django.core.files import File
from django.core.files.move import file_move_safe
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.six import string_types

from media_trash.storage import FileSystemStorage
from .namers import get_namer
from .settings import EXTENSIONS, VERSIONS, ADMIN_VERSIONS, VERSIONS_BASEDIR, VERSION_QUALITY, STRICT_PIL, \
    IMAGE_MAXBLOCK, DEFAULT_PERMISSIONS, MEDIA_TRASH_URL
from .utils import path_strip, process_image, get_modified_time

if STRICT_PIL:
    from PIL import Image
    from PIL import ImageFile
else:
    try:
        from PIL import Image
        from PIL import ImageFile
    except ImportError:
        import Image
        import ImageFile

ImageFile.MAXBLOCK = IMAGE_MAXBLOCK  # default is 64k


class FileListing(object):
    """
    The FileListing represents a group of FileObjects/FileDirObjects.

    An example::

        from filebrowser.base import FileListing
        filelisting = FileListing(path, sorting_by='date', sorting_order='desc')
        print filelisting.files_listing_total()
        print filelisting.results_listing_total()
        for fileobject in filelisting.files_listing_total():
            print fileobject.filetype

    where path is a relative path to a storage location
    """
    # Four variables to store the length of a listing obtained by various listing methods
    # (updated whenever a particular listing method is called).
    _results_listing_total = None
    _results_walk_total = None
    _results_listing_filtered = None
    _results_walk_total = None

    def __init__(self, path, filter_func=None, sorting_by=None, sorting_order=None, storage=None):
        self.path = os.path.normpath(path)
        self.filter_func = filter_func
        self.sorting_by = sorting_by
        self.sorting_order = sorting_order
        if not storage:
            storage = FileSystemStorage(self.path, base_url=MEDIA_TRASH_URL)
        self.storage = storage
        self.directory = path

    # HELPER METHODS
    # sort_by_attr

    def sort_by_attr(self, seq, attr):
        """
        Sort the sequence of objects by object's attribute

        Arguments:
        seq  - the list or any sequence (including immutable one) of objects to sort.
        attr - the name of attribute to sort by

        Returns:
        the sorted list of objects.
        """
        from operator import attrgetter
        if isinstance(attr, string_types):  # Backward compatibility hack
            attr = (attr,)
        return sorted(seq, key=attrgetter(*attr))

    @cached_property
    def is_folder(self):
        return self.storage.isdir(self.path)

    def listing(self):
        """List all files for path"""
        if self.is_folder:
            dirs, files = self.storage.listdir(self.path)
            return (f for f in dirs + files)
        return []

    def _walk(self, path, filelisting):
        """
        Recursively walks the path and collects all files and
        directories.

        Danger: Symbolic links can create cycles and this function
        ends up in a regression.
        """
        dirs, files = self.storage.listdir(path)

        if dirs:
            for d in dirs:
                self._walk(os.path.join(path, d), filelisting)
                filelisting.extend([path_strip(os.path.join(path, d), self.directory)])

        if files:
            for f in files:
                filelisting.extend([path_strip(os.path.join(path, f), self.directory)])

    def walk(self):
        """Walk all files for path"""
        filelisting = []
        if self.is_folder:
            self._walk(self.path, filelisting)
        return filelisting

    # Cached results of files_listing_total (without any filters and sorting applied)
    _fileobjects_total = None

    def files_listing_total(self):
        """Returns FileObjects for all files in listing"""
        if self._fileobjects_total is None:
            self._fileobjects_total = []
            for item in self.listing():
                fileobject = FileObject(os.path.join(self.path, item),
                                        storage=self.storage)
                self._fileobjects_total.append(fileobject)

        files = self._fileobjects_total

        if self.sorting_by:
            files = self.sort_by_attr(files, self.sorting_by)
        if self.sorting_order == "desc":
            files.reverse()

        self._results_listing_total = len(files)
        return files

    def files_walk_total(self):
        """Returns FileObjects for all files in walk"""
        files = []
        for item in self.walk():
            fileobject = FileObject(os.path.join(self.directory, item),
                                    storage=self.storage)
            files.append(fileobject)
        if self.sorting_by:
            files = self.sort_by_attr(files, self.sorting_by)
        if self.sorting_order == "desc":
            files.reverse()
        self._results_walk_total = len(files)
        return files

    def files_listing_filtered(self):
        """Returns FileObjects for filtered files in listing"""
        if self.filter_func:
            listing = list(filter(self.filter_func, self.files_listing_total()))
        else:
            listing = self.files_listing_total()
        self._results_listing_filtered = len(listing)
        return listing

    def files_walk_filtered(self):
        """Returns FileObjects for filtered files in walk"""
        if self.filter_func:
            listing = list(filter(self.filter_func, self.files_walk_total()))
        else:
            listing = self.files_walk_total()
        self._results_walk_filtered = len(listing)
        return listing

    def results_listing_total(self):
        """Counter: all files"""
        if self._results_listing_total is not None:
            return self._results_listing_total
        return len(self.files_listing_total())

    def results_walk_total(self):
        """Counter: all files"""
        if self._results_walk_total is not None:
            return self._results_walk_total
        return len(self.files_walk_total())

    def results_listing_filtered(self):
        """Counter: filtered files"""
        if self._results_listing_filtered is not None:
            return self._results_listing_filtered
        return len(self.files_listing_filtered())

    def results_walk_filtered(self):
        """Counter: filtered files"""
        if self._results_walk_filtered is not None:
            return self._results_walk_filtered
        return len(self.files_walk_filtered())


class FileObject(object):
    """
    The FileObject represents a file (or directory) on the server.

    An example::

        from filebrowser.base import FileObject
        fileobject = FileObject(path)

    where path is a relative path to a storage location
    """

    def __init__(self, path, storage=None):
        self.storage = storage
        self.path = os.path.normpath(path)
        self.head = os.path.dirname(path)
        self.filename = os.path.basename(path)
        self.filename_lower = self.filename.lower()
        self.filename_root, self.extension = os.path.splitext(self.filename)
        self.mimetype = mimetypes.guess_type(self.filename)
        self.directory = storage.location

    def __str__(self):
        return force_text(self.path)

    @property
    def name(self):
        return self.path

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self or "None")

    def __len__(self):
        return len(self.path)

    # HELPER METHODS
    # _get_file_type

    def _get_file_type(self):
        """Get file type as defined in EXTENSIONS."""
        file_type = ''
        for k, v in EXTENSIONS.items():
            for extension in v:
                if self.extension.lower() == extension.lower():
                    file_type = k
        return file_type

    # GENERAL ATTRIBUTES/PROPERTIES
    # filetype
    # filesize
    # date
    # datetime
    # exists

    @cached_property
    def filetype(self):
        """Filetype as defined with EXTENSIONS"""
        return 'Folder' if self.is_folder else self._get_file_type()

    @cached_property
    def filesize(self):
        """Filesize in bytes"""
        return self.storage.size(self.path) if self.exists else None

    @cached_property
    def date(self):
        """Modified time (from storage) as float (mktime)"""
        if self.exists:
            return time.mktime(get_modified_time(self.storage, self.path).timetuple())
        return None

    @property
    def datetime(self):
        """Modified time (from storage) as datetime"""
        if self.date:
            return datetime.datetime.fromtimestamp(self.date)
        return None

    @cached_property
    def exists(self):
        """True, if the path exists, False otherwise"""
        return self.storage.exists(self.path)

    def move(self, dst, replace=False):
        """Move this file to another location"""
        dstdir = os.path.dirname(dst)

        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)

        # The file already exists, so we need to avoid name conflict.
        if not replace and os.path.isfile(dst):
            filename = os.path.basename(dst)
            fname, ext = os.path.splitext(filename)
            dst = os.path.join(dstdir, fname.rstrip("-") + timezone.now().strftime("-%Y-%m-%d-%H%M%S") + ext)

        file_move_safe(self.storage.path(self.path), dst,
                       allow_overwrite=True)

    # PATH/URL ATTRIBUTES/PROPERTIES
    # path (see init)
    # path_relative_directory
    # path_full
    # dirname
    # url

    @property
    def path_relative_directory(self):
        """Path relative to directory"""
        return path_strip(self.path, self.directory)

    @property
    def path_full(self):
        """Absolute path as defined with storage"""
        return self.storage.path(self.path)

    @property
    def dirname(self):
        """The directory (not including directory)"""
        return os.path.dirname(self.path_relative_directory)

    @property
    def url(self):
        """URL for the file/folder as defined with storage"""
        return self.storage.url(self.path_relative_directory)

    # IMAGE ATTRIBUTES/PROPERTIES
    # dimensions
    # width
    # height
    # aspectratio
    # orientation

    @cached_property
    def dimensions(self):
        """Image dimensions as a tuple"""
        if self.filetype != 'Image':
            return None
        try:
            im = Image.open(self.storage.open(self.path))
            return im.size
        except:
            pass

    @property
    def width(self):
        """Image width in px"""
        if self.dimensions:
            return self.dimensions[0]
        return None

    @property
    def height(self):
        """Image height in px"""
        if self.dimensions:
            return self.dimensions[1]
        return None

    @property
    def aspectratio(self):
        """Aspect ratio (float format)"""
        if self.dimensions:
            return float(self.width) / float(self.height)
        return None

    @property
    def orientation(self):
        """Image orientation, either 'Landscape' or 'Portrait'"""
        if self.dimensions:
            if self.dimensions[0] >= self.dimensions[1]:
                return "Landscape"
            else:
                return "Portrait"
        return None

    # FOLDER ATTRIBUTES/PROPERTIES
    # is_folder
    # is_empty

    @cached_property
    def is_folder(self):
        """True, if path is a folder"""
        return self.storage.isdir(self.path)

    @property
    def is_empty(self):
        """True, if folder is empty. False otherwise, or if the object is not a folder."""
        if self.is_folder:
            dirs, files = self.storage.listdir(self.path)
            if not dirs and not files:
                return True
        return False

    # VERSION ATTRIBUTES/PROPERTIES
    # is_version
    # versions_basedir
    # original
    # original_filename

    @property
    def is_version(self):
        """True if file is a version, false otherwise"""
        return self.head.startswith(VERSIONS_BASEDIR)

    @property
    def versions_basedir(self):
        """Main directory for storing versions (either VERSIONS_BASEDIR or directory)"""
        if VERSIONS_BASEDIR:
            return VERSIONS_BASEDIR
        elif self.directory:
            return self.directory
        else:
            return ""

    @property
    def original(self):
        """Returns the original FileObject"""
        if self.is_version:
            relative_path = self.head.replace(self.versions_basedir, "").lstrip("/")
            return FileObject(os.path.join(self.directory, relative_path, self.original_filename),
                              storage=self.storage)
        return self

    @property
    def original_filename(self):
        """Get the filename of an original image from a version"""
        if not self.is_version:
            return self.filename
        return get_namer(
            file_object=self,
            filename_root=self.filename_root,
            extension=self.extension,
        ).get_original_name()

    # VERSION METHODS
    # versions()
    # admin_versions()
    # version_name(suffix)
    # version_path(suffix)
    # version_generate(suffix)

    def _get_options(self, version_suffix, extra_options=None):
        options = dict(VERSIONS.get(version_suffix, {}))
        if extra_options:
            options.update(extra_options)
        if 'size' in options and 'width' not in options:
            width, height = options['size']
            options['width'] = width
            options['height'] = height
        return options

    def versions(self):
        """List of versions (not checking if they actually exist)"""
        version_list = []
        if self.filetype == "Image" and not self.is_version:
            for version in sorted(VERSIONS):
                version_list.append(os.path.join(self.versions_basedir, self.dirname, self.version_name(version)))
        return version_list

    def admin_versions(self):
        """List of admin versions (not checking if they actually exist)"""
        version_list = []
        if self.filetype == "Image" and not self.is_version:
            for version in ADMIN_VERSIONS:
                version_list.append(os.path.join(self.versions_basedir, self.dirname, self.version_name(version)))
        return version_list

    def version_name(self, version_suffix, extra_options=None):
        """Name of a version"""
        # FIXME: version_name for version?
        options = self._get_options(version_suffix, extra_options)
        return get_namer(
            file_object=self,
            version_suffix=version_suffix,
            filename_root=self.filename_root,
            extension=self.extension,
            options=options,
        ).get_version_name()

    def version_path(self, version_suffix, extra_options=None):
        """Path to a version (relative to storage location)"""
        # FIXME: version_path for version?
        return os.path.join(
            self.versions_basedir,
            self.dirname,
            self.version_name(version_suffix, extra_options))

    def version_generate(self, version_suffix, extra_options=None):
        """Generate a version"""  # FIXME: version_generate for version?
        path = self.path
        options = self._get_options(version_suffix, extra_options)

        version_path = self.version_path(version_suffix, extra_options)
        if not self.storage.isfile(version_path):
            version_path = self._generate_version(version_path, options)
        elif get_modified_time(self.storage, path) > get_modified_time(self.storage, version_path):
            version_path = self._generate_version(version_path, options)
        return FileObject(version_path, storage=self.storage)

    def _generate_version(self, version_path, options):
        """
        Generate Version for an Image.
        value has to be a path relative to the storage location.
        """

        tmpfile = File(tempfile.NamedTemporaryFile())

        try:
            f = self.storage.open(self.path)
        except IOError:
            return ""
        im = Image.open(f)
        version_dir, version_basename = os.path.split(version_path)
        root, ext = os.path.splitext(version_basename)
        version = process_image(im, options)
        if not version:
            version = im
        if 'methods' in options:
            for m in options['methods']:
                if callable(m):
                    version = m(version)

        # IF need Convert RGB
        if ext in [".jpg", ".jpeg"] and version.mode not in ("L", "RGB"):
            version = version.convert("RGB")

        # save version
        try:
            version.save(tmpfile, format=Image.EXTENSION[ext.lower()], quality=VERSION_QUALITY,
                         optimize=(os.path.splitext(version_path)[1] != '.gif'))
        except IOError:
            version.save(tmpfile, format=Image.EXTENSION[ext.lower()], quality=VERSION_QUALITY)
        # remove old version, if any
        if version_path != self.storage.get_available_name(version_path):
            self.storage.delete(version_path)
        self.storage.save(version_path, tmpfile)
        # set permissions
        if DEFAULT_PERMISSIONS is not None:
            os.chmod(self.storage.path(version_path), DEFAULT_PERMISSIONS)
        return version_path

    # DELETE METHODS
    # delete()
    # delete_versions()
    # delete_admin_versions()

    def delete(self):
        """Delete FileObject (deletes a folder recursively)"""
        if self.is_folder:
            self.storage.rmtree(self.path)
        else:
            self.storage.delete(self.path)

    def delete_versions(self):
        """Delete versions"""
        for version in self.versions():
            try:
                self.storage.delete(version)
            except:
                pass

    def delete_admin_versions(self):
        """Delete admin versions"""
        for version in self.admin_versions():
            try:
                self.storage.delete(version)
            except:
                pass
