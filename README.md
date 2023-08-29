# tkfilechk
feed it a directory full of files and it makes a checklist with notes

Launch with ``--path`` pointing to a directory full of files you need to inspect.  (Optional ``--recurse`` parameter.)

Spacebar toggles the checked state.

Colon edits note for selected file.

Double-click opens the file with the default association.

---

Restrict file list to only include files with certain extension using ``--ext``.  Can be used multiple times. Example:

    python tkfilechk.py --ext wav --ext mp3

The leading dot ``.`` is not required.

---

Light or dark Azure.tcl theme can be used with ``--theme light`` or ``--theme dark`` options. The default tkinter theme performs slightly faster so don't use these options on very large lists if scrolling becomes slow.

---

``--no-rescan`` flag can be added to prevent re-scanning the directory.  It will be scanned at least once if the database file does not exist.

---

Database files are named ``_filechk.db`` and stored inside the folder given by the ``--path`` argument.  (Default path is your user's Music folder.)

---

Double-click the vbs file to run from explorer.  Suggestion is to create a shortcut to it.  Edit the ``tkfilechk.cmd`` to adjust command-line options.  These files are expected to live in the default location that the GitHub app puts them so if you keep them elsewhere you will need to edit the paths accordingly.  (GitHub app clones to a folder named GitHub in your Documents folder so the vbs launcher is hardcoded to point to ``c:\Users\<username>\Documents\GitHub\tkfilechk\tkfilechk.cmd``.)

---

There has been no effort to make this work on anything other than Windows since at this point I am the only one expected to be using this.  Open an issue and I may change this to be cross-platform.
