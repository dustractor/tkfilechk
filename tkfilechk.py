# version 0.1
import tkinter as tk
import tkinter.ttk as ttk
import sqlite3,pathlib,os,argparse,datetime
from collections import namedtuple

args = argparse.ArgumentParser()
args.add_argument("--path",
                  type=pathlib.Path,
                  default=pathlib.Path.home()/"Music")
args.add_argument("--recurse",
                  action="store_true")
args.add_argument("--ext",
                  action="append")
args.add_argument("--theme",
                  choices=["light","dark"])
args.add_argument("--no-rescan",action="store_true")


ns = args.parse_args()

DBPATH = ns.path / "_filechk.db"

EXTENSIONS = set()
if ns.ext:
    for ext in ns.ext:
        if not ext.startswith("."):
            t = "." + ext
        else:
            t = ext
        EXTENSIONS.add(t)

UNCHECKED = "\u2610"
CHECKED = "\u2612"

class ItemsLibrarian(sqlite3.Connection):

    ddl = """
    create table if not exists items(
    id integer primary key,
    path text,
    name text,
    mtime real,
    size integer,
    status text default "0",
    notes text default "",
    unique (path,mtime,size) on conflict ignore);"""

    def __init__(self,name,**kwargs):
        super().__init__(name,**kwargs)
        self.cu = self.cursor()
        self.cu.row_factory = lambda c,r:r[0]
        self.executescript(self.ddl)
        self.commit()

def iter_paths(path,recurse):
    if not recurse:
        for p in path.iterdir():
            if p.is_file():
                yield p
    else:
        for r,ds,fs in os.walk(path):
            for f in fs:
                p = pathlib.Path(r) / f
                yield p

Values = namedtuple(
    "logicalcolumns",
    "oid path name mtime modified size status notes check")

class Library:
    _handle = None
    @property
    def cx(self):
        if not self._handle:
            self._handle = sqlite3.connect(
                DBPATH,
                factory=ItemsLibrarian)
        return self._handle
    def populate_from(self,path,recurse):
        print("populating from path:",path)
        for p in iter_paths(path,recurse):
            if p == DBPATH:
                continue
            if EXTENSIONS and p.suffix not in EXTENSIONS:
                continue
            stats = p.stat()
            self.cx.execute(
                "insert into items (path,name,mtime,size) values (?,?,?,?)",
                (str(p),
                 p.name,
                 stats.st_mtime,
                 stats.st_size))
        self.cx.commit()
    def view(self):
        yield from self.cx.execute(
            "select id,path,name,mtime,size,status,notes from items order by mtime")
    def set_status(self,oid,status):
        self.cx.execute(
            "update items set status=? where id=?",
            (status,oid))
        self.cx.commit()
    def set_notes(self,oid,notes):
        self.cx.execute(
            "update items set notes=? where id=?",
            (notes,oid))
        self.cx.commit()


db = Library()
if not DBPATH.is_file() or not ns.no_rescan:
    db.populate_from(ns.path,ns.recurse)

class App(tk.Tk):
    @property
    def selection_data(self):
        selection = self.tree.selection()
        return Values(*self.tree.item(selection,"values"))
    @selection_data.setter
    def selection_data(self,values):
        self.tree.item(self.tree.selection(),values=values)
    def treeview_select(self,event):
        selection = self.tree.selection()
    def toggle_state(self,event):
        v = self.selection_data
        status = v.status
        status = "1" if status == "0" else "0"
        db.set_status(v.oid,status)
        check = [UNCHECKED,CHECKED][status=="1"]
        v = v._replace(status=status,check=check)
        self.selection_data = v
    def fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        for oid,path,name,mtime,size,status,notes in db.view():
            modified = datetime.datetime.fromtimestamp(
                mtime,tz=datetime.timezone.utc)
            check = [UNCHECKED,CHECKED][status=="1"]
            self.tree.insert(
                "","end",
                text=name,
                values=(oid,path,name,mtime,modified,size,status,notes,check))
    def item_inspect(self,event):
        os.startfile(self.selection_data.path)
    def win_destroy_callback(self,*args):
        v = self.selection_data
        t = self.win.textbox.get("1.0","end")
        v = v._replace(notes=t)
        db.set_notes(v.oid,v.notes)
        self.selection_data = v
        self.win.destroy()
    def notes_edit(self,event):
        v = self.selection_data
        self.win = tk.Toplevel(self)
        self.win.frame = ttk.Labelframe(self.win,text=v.name)
        self.win.frame.pack()
        self.win.textbox = tk.Text(self.win.frame)
        self.win.textbox.pack()
        self.win.textbox.insert("1.0",v.notes)
        self.win.protocol("WM_DELETE_WINDOW",self.win_destroy_callback)
        self.win.bind("<Escape>",self.win_destroy_callback)
        self.win.textbox.focus()
    def __init__(self):
        super().__init__()
        self.file_ls = tk.StringVar()
        self.title(ns.path.name)
        self.mainframe = ttk.Labelframe(self,text=str(ns.path))
        self.mainframe.pack(fill="both",expand=True)
        self.scrollbar = ttk.Scrollbar(self.mainframe)
        self.tree = ttk.Treeview(self.mainframe,yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)
        self.tree.pack(side="left",fill="both",expand=True)
        self.scrollbar.pack(side="right",fill="y",expand=True)
        self.tree.bind("<<TreeviewSelect>>",self.treeview_select)
        self.tree.bind("<space>",self.toggle_state)
        self.tree.bind("<colon>",self.notes_edit)
        self.tree.bind("<Double-1>",self.item_inspect)
        self.tree.config(
            columns=("oid","path","name","mtime","modified","size","status","notes","check"),
             displaycolumns=("modified","size","notes","check"))
        self.tree.heading("name",text="name")
        self.tree.heading("modified",text="modified")
        self.tree.heading("size",text="size")
        self.tree.heading("notes",text="notes")
        self.tree.heading("check",text="state")
        self.fill_tree()

if __name__ == "__main__":
    app = App()
    if ns.theme == "dark":
        app.tk.call("source", "azure.tcl")
        app.tk.call("set_theme", "dark")
    elif ns.theme == "light":
        app.tk.call("source", "azure.tcl")
        app.tk.call("set_theme", "light")
    app.mainloop()

