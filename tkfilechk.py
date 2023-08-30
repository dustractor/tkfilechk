# version 0.2
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
import sqlite3,pathlib,os,argparse
from datetime import datetime,timezone
from collections import namedtuple
from xml.dom import minidom

#{{{1 args
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
#}}}1

#{{{1 globals
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

#}}}1

def mtime_fmt(mtime):
    return datetime.fromtimestamp(mtime,tz=timezone.utc)

#{{{1 minidom setup
def _elem_inplace_addition(self,other):
    self.appendChild(other)
    return self
def _elem_textnode(self,text):
    textnode = self.ownerDocument.createTextNode(text)
    self.appendChild(textnode)
    return self
def _elem_set_attributes_from_tuple(self,*args):
    for k,v in args:
        self.setAttribute(k,str(v))
    return self
minidom.Element.__iadd__ = _elem_inplace_addition
minidom.Element.txt = _elem_textnode
minidom.Element.attrt = _elem_set_attributes_from_tuple
minidom.Element.__str__ = lambda s:s.toprettyxml().strip()

#}}}1

#{{{1 ItemsLibrarian
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

#}}}1

#{{{1 iter_paths

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


#}}}1

#{{{1 RowNames namedtuple

RowNames = namedtuple(
    "rowhandles",
    "oid path name mtime size status notes")

#}}}1

#{{{1 TreeValues namedtuple

TreeValues = namedtuple(
    "logicalcolumns",
    "oid path name modified size status notes check")

#}}}1

#{{{1 Library

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
    def view(self,order=None,reverse=False):
        if not order:
            order_clause = ""
        else:
            order_clause = "order by " + order
            if reverse:
                order_clause += " DESC"
        for t in self.cx.execute(
            "select id,path,name,mtime,size,status,notes from items %s" % (
            order_clause)):
            yield RowNames(*t)
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
    def notes_export_view(self):
        yield from self.cx.execute(
            "select path,name,mtime,size,status,notes "
            "from items where notes is not ''")
    def count_items_with_notes(self):
        return self.cx.cu.execute(
            "select count(*) from items where notes is not ''").fetchone()



#}}}1

#{{{1 instantiate db
db = Library()

if not DBPATH.is_file() or not ns.no_rescan:
    db.populate_from(ns.path,ns.recurse)
#}}}1

#{{{1 Toolbar
class Toolbar(ttk.Frame):
    def app_quit(self):
        self.quit()
    def export_annotated_to_html(self):
        output_file = filedialog.asksaveasfilename(
            title="Export annotated to html",
            defaultextension="html",
            initialdir=ns.path)
        if output_file == "":
            print("cancelled save")
            return
        print("output_file:",output_file)
        if db.count_items_with_notes() == 0:
            print("no items have notes. export cancelled")
            return
        doc = minidom.Document()
        elem = doc.createElement
        root = elem("html")
        head = elem("head")
        root += head
        title = elem("title")
        head += title
        title.txt(str(ns.path) + " annotation")
        body = elem("body")
        root += body
        ul = elem("ul")
        body += ul
        for path,name,mtime,size,status,notes in db.notes_export_view():
            li = elem("li")
            ul += li
            h = elem("h3")
            h.txt(name)
            li += h
            a = elem("a")
            li += a
            a.attrt(("href","file:///"+path))
            a.txt(path)
            for line in notes.splitlines():
                p = elem("p")
                li += p
                p.txt(line)
        with open(output_file,"w") as f:
            f.write(str(root))
        os.startfile(output_file)
    def __init__(self,master):
        super().__init__(master)
        self.menubutton = ttk.Menubutton(self,text="Commands")
        self.menubutton.pack(anchor="w")
        self.menubutton.menu = tk.Menu(self.menubutton,tearoff=False)
        self.menubutton["menu"] = self.menubutton.menu
        menu = self.menubutton.menu
        menu.add_command(command=self.app_quit,
                         label="Exit",
                         accelerator="Ctrl+Q")
        menu.add_command(command=self.export_annotated_to_html,
                         label="Export annotated to html (notes.html)")
        
#}}}1

#{{{1 App
class App(tk.Tk):
    @property
    def selection_data(self):
        selection = self.tree.selection()
        return TreeValues(*self.tree.item(selection,"values"))
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
    def fill_tree(self,order=None,reverse=False):
        self.tree.delete(*self.tree.get_children())
        for t in db.view(order,reverse):
            modified = mtime_fmt(t.mtime)
            check = [UNCHECKED,CHECKED][t.status=="1"]
            if t.size < 1024:
                size = "%d bytes"%t.size
            elif t.size < (1024 ** 2):
                size = "%dKB"%round(t.size/1024,3)
            elif t.size < (1024 ** 3):
                size = "%dMB"%round(t.size/1024**2,3)
            elif t.size < (1024 ** 4):
                size = "%dGB"%round(t.size/1024**3,3)
            self.tree.insert("","end",text=t.name,
                values=(
                    t.oid,t.path,t.name,modified,size,t.status,t.notes,check))
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
    def sort_by_name(self):
        cur_order = self.order_by.get()
        if cur_order != "name":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("name")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def sort_by_mtime(self):
        cur_order = self.order_by.get()
        if cur_order != "mtime":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("mtime")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def sort_by_size(self):
        cur_order = self.order_by.get()
        if cur_order != "size":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("size")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def sort_by_notes(self):
        cur_order = self.order_by.get()
        if cur_order != "notes":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("notes")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def sort_by_status(self):
        cur_order = self.order_by.get()
        if cur_order != "status":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("status")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def sort_by_path(self):
        cur_order = self.order_by.get()
        if cur_order != "path":
            self.order_reversed.set(0)
        else:
            self.order_reversed.set(int(not bool(self.order_reversed.get())))
        self.order_by.set("path")
        self.fill_tree(self.order_by.get(),self.order_reversed.get())
    def __init__(self):
        super().__init__()
        self.order_by = tk.StringVar()
        self.order_reversed = tk.IntVar()
        self.file_ls = tk.StringVar()
        self.title(ns.path.name)
        self.toolbar = Toolbar(self)
        self.toolbar.pack(fill="x")
        self.mainframe = ttk.Labelframe(self,text=str(ns.path))
        self.mainframe.pack(fill="both",expand=True)
        self.scrollbar = ttk.Scrollbar(self.mainframe)
        self.tree = ttk.Treeview(self.mainframe,
                                 yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)
        self.tree.pack(side="left",fill="both",expand=True)
        self.scrollbar.pack(side="right",fill="y",expand=True)
        self.bind("<Control-q>",lambda *_:self.quit())
        self.bind("<Control-w>",lambda *_:self.quit())
        self.tree.bind("<<TreeviewSelect>>",self.treeview_select)
        self.tree.bind("<space>",self.toggle_state)
        self.tree.bind("<colon>",self.notes_edit)
        self.tree.bind("<Double-1>",self.item_inspect)
        self.tree.bind("<Return>",self.item_inspect)
        self.tree.config(
            columns=TreeValues._fields,
             displaycolumns=("path","modified","size","notes","check"))
        self.tree.heading("#0",text="name",command=self.sort_by_name)
        self.tree.heading("modified",text="modified",command=self.sort_by_mtime)
        self.tree.heading("path",text="path",command=self.sort_by_path)
        self.tree.heading("size",text="size",command=self.sort_by_size)
        self.tree.heading("notes",text="notes",command=self.sort_by_notes)
        self.tree.heading("check",text="state",command=self.sort_by_status)
        self.fill_tree()

#}}}1

#{{{1 main guard
if __name__ == "__main__":
    app = App()
    if ns.theme == "dark":
        app.tk.call("source", "azure.tcl")
        app.tk.call("set_theme", "dark")
    elif ns.theme == "light":
        app.tk.call("source", "azure.tcl")
        app.tk.call("set_theme", "light")
    app.mainloop()

