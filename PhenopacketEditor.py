#imports-----
# test github
import ctypes
import wx
import wx.adv
import requests
import wx.lib.mixins.listctrl as listmix
import json
import locale
import datetime
import sys

from google.protobuf.json_format import Parse, ParseError
from phenopackets import Phenopacket

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

KARYOTYPE_CHOICES = [
    "UNKNOWN_KARYOTYPE",
    "XX",
    "XY",
    "XO",
    "XXY",
    "XXX",
    "XXYY",
    "XXXY",
    "XXXX",
    "XYY",
    "OTHER_KARYOTYPE"
]

SEX_CHOICES = [
    "UNKNOWN_SEX",
    "MALE",
    "FEMALE",
    "OTHER_SEX"
]

class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        listmix.TextEditMixin.__init__(self)

class HPOSelectionDialog(wx.Dialog):
    def __init__(self, parent, pheno_list):
        super().__init__(parent, title="Select HPO Terms", size=(600, 500))
        self.pheno_list = pheno_list
        self.api_results = []

        vbox = wx.BoxSizer(wx.VERTICAL)

        # Search controls
        hbox_search = wx.BoxSizer(wx.HORIZONTAL)
        self.search_ctrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.search_btn = wx.Button(self, label="Search HPO")
        hbox_search.Add(self.search_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        hbox_search.Add(self.search_btn, 0)
        vbox.Add(hbox_search, 0, wx.EXPAND | wx.ALL, 5)

        # Results list
        self.results_list = wx.ListBox(self, style=wx.LB_MULTIPLE)
        vbox.Add(self.results_list, 1, wx.EXPAND | wx.ALL, 5)

        # Add button
        self.add_btn = wx.Button(self, label="Add Selected to List")
        vbox.Add(self.add_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)

     
        self.close_btn = wx.Button(self, label="Close")
        vbox.Add(self.close_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetSizer(vbox)

        # Bind events
        self.search_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_search)
        self.search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add_selected)
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)

    def on_search(self, event):
        keyword = self.search_ctrl.GetValue().strip()
        if not keyword:
            wx.MessageBox("Enter a search term.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

    
        max_list = 100


        url = f"https://clinicaltables.nlm.nih.gov/api/hpo/v3/search?terms={keyword}&maxList={max_list}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # ClinicalTables returns [num_found, ids, labels, ...]
            ids = data[1] if len(data) > 1 else []
            hpo_terms = data[3] if len(data) > 3 else []  
            display_items = [f"{hpo_id} - {label}" for hpo_id, label in hpo_terms]
            self.results_list.Set(display_items)
            self.api_results = hpo_terms  # Store for later processing

            if not ids:
                wx.MessageBox("No HPO terms matched your search.", "No Results", wx.OK | wx.ICON_INFORMATION)
                self.results_list.Set([])
                self.api_results = []
                return

        except Exception as e:
            wx.MessageBox(f"Error fetching HPO terms: {e}", "API Error", wx.OK | wx.ICON_ERROR)
            self.results_list.Set([])
            self.api_results = []

    def on_add_selected(self, event):
        selections = self.results_list.GetSelections()
        if not selections:
            wx.MessageBox("Please select at least one HPO term to add.", "No Selection", wx.OK | wx.ICON_INFORMATION)
            return

        # Gather existing (id, label) pairs to avoid duplicates
        existing = set()
        for i in range(self.pheno_list.GetItemCount()):
            existing.add((self.pheno_list.GetItemText(i), self.pheno_list.GetItem(i, 1).GetText()))

        added = 0
        for idx in selections:
            hpo_id, hpo_label = self.api_results[idx]
            if (hpo_id, hpo_label) not in existing:
                row = self.pheno_list.InsertItem(self.pheno_list.GetItemCount(), hpo_id)
                self.pheno_list.SetItem(row, 1, hpo_label)
                added += 1

        if added:
            wx.MessageBox(f"Added {added} new HPO term(s) to the phenotypic features list.", "Success", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("No new HPO terms were added (all selected terms are already present).", "Info", wx.OK | wx.ICON_INFORMATION)

    def on_close(self, event):
        self.EndModal(wx.ID_CLOSE)

class PhenopacketEditor(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(700, 1000))
        self.panel = wx.Panel(self)
        self.json_data = {}
        self.file_path = None

        vbox = wx.BoxSizer(wx.VERTICAL)

        # File controls
        hbox_file = wx.BoxSizer(wx.HORIZONTAL)
        self.open_btn = wx.Button(self.panel, label='Open JSON')
        self.save_btn = wx.Button(self.panel, label='Save JSON')
        hbox_file.Add(self.open_btn, flag=wx.RIGHT, border=5)
        hbox_file.Add(self.save_btn)
        vbox.Add(hbox_file, flag=wx.ALL, border=10)

        # Subject fields
        self.subject_id = wx.TextCtrl(self.panel)
        self.subject_sex = wx.Choice(self.panel, choices=SEX_CHOICES)
        self.karyotype_choice = wx.Choice(self.panel, choices=KARYOTYPE_CHOICES)
        self.subject_dob = wx.TextCtrl(self.panel)



    


        grid = wx.FlexGridSizer(4, 2, 10, 10)
        grid.AddGrowableCol(1, 1)
        grid.AddMany([
            (wx.StaticText(self.panel, label="Subject ID:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.subject_id, 1, wx.EXPAND),
            (wx.StaticText(self.panel, label="Sex:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.subject_sex, 1, wx.EXPAND),
            (wx.StaticText(self.panel, label="Karyotypic Sex:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.karyotype_choice, 1, wx.EXPAND),
            (wx.StaticText(self.panel, label="Date of Birth:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.subject_dob, 1, wx.EXPAND),
        ])
        vbox.Add(grid, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Phenotypic features
        vbox.Add(wx.StaticText(self.panel, label="Phenotypic Features (HPO ID and Label):"), flag=wx.LEFT | wx.TOP, border=10)
        hbox_pheno = wx.BoxSizer(wx.HORIZONTAL)
        self.pheno_list = EditableListCtrl(self.panel)
        self.pheno_list.InsertColumn(0, "HPO ID", width=150)
        self.pheno_list.InsertColumn(1, "HPO Label", width=300)
        hbox_pheno.Add(self.pheno_list, 1, wx.EXPAND)
        pheno_btns = wx.BoxSizer(wx.VERTICAL)
        self.add_pheno_btn = wx.Button(self.panel, label="Add HPO Terms")
        self.remove_pheno_btn = wx.Button(self.panel, label="Remove Selected")
        self.copy_hpo_btn = wx.Button(self.panel, label="Copy HPOs to clipboard")

        pheno_btns.Add(self.add_pheno_btn, flag=wx.BOTTOM, border=5)
        pheno_btns.Add(self.remove_pheno_btn)
        pheno_btns.Add(self.copy_hpo_btn, flag=wx.TOP, border=5)
        
        hbox_pheno.Add(pheno_btns, flag=wx.LEFT, border=5)
        vbox.Add(hbox_pheno, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Metadata
        vbox.Add(wx.StaticText(self.panel, label="Created By:"), flag=wx.LEFT | wx.TOP, border=10)
        self.created_by = wx.TextCtrl(self.panel)
        vbox.Add(self.created_by, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        self.panel.SetSizer(vbox)

        # Bind events
        self.open_btn.Bind(wx.EVT_BUTTON, self.on_open)
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        self.add_pheno_btn.Bind(wx.EVT_BUTTON, self.on_add_pheno)
        self.remove_pheno_btn.Bind(wx.EVT_BUTTON, self.on_remove_pheno)
        self.copy_hpo_btn.Bind(wx.EVT_BUTTON, self.on_copy_hpos)


    def on_open(self, event):
        with wx.FileDialog(self, "Open Phenopacket JSON", wildcard="JSON files (*.json)|*.json",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.file_path = dlg.GetPath()
                with open(self.file_path, 'r') as f:
                    self.json_data = json.load(f)
                self.populate_fields()

    def populate_fields(self):
        subj = self.json_data.get('subject', {})
        self.subject_id.SetValue(subj.get('id', ''))
        
        sex = subj.get('sex', '')
        if sex in SEX_CHOICES:
            self.subject_sex.SetStringSelection(sex)
        else:
            self.subject_sex.SetSelection(0)  # Default to UNKNOWN_SEX

        karyotype = subj.get('karyotypic_sex', '')
        if karyotype in KARYOTYPE_CHOICES:
            self.karyotype_choice.SetStringSelection(karyotype)
        else:
            self.karyotype_choice.SetSelection(0)


            import datetime

        dob_str = subj.get('date_of_birth', '')
        if dob_str:
            try:
                # Parse the full ISO 8601 format with time and 'Z'
            
                dob = datetime.datetime.strptime(dob_str, "%Y-%m-%dT%H:%M:%SZ").date()
                # Format for locale display
             
                locale.setlocale(locale.LC_TIME, '')
                formatted = dob.strftime(locale.nl_langinfo(locale.D_FMT))
                self.subject_dob.SetValue(formatted)
            except Exception:
                self.subject_dob.SetValue('')
        else:
            self.subject_dob.SetValue('')

        
        # Phenotypic features
        self.pheno_list.DeleteAllItems()
        phenos = self.json_data.get('phenotypicFeatures', [])
        for p in phenos:
            t = p.get('type', {})
            idx = self.pheno_list.InsertItem(self.pheno_list.GetItemCount(), t.get('id', ''))
            self.pheno_list.SetItem(idx, 1, t.get('label', ''))
        meta = self.json_data.get('metaData', {})
        self.created_by.SetValue(meta.get('createdBy', ''))


    def on_add_pheno(self, event):
        dlg = HPOSelectionDialog(self, self.pheno_list)
        if dlg.ShowModal() == wx.ID_OK:
            selected = dlg.get_selected_terms()
            # Avoid duplicates
            existing = set()
            for i in range(self.pheno_list.GetItemCount()):
                existing.add((self.pheno_list.GetItemText(i), self.pheno_list.GetItem(i, 1).GetText()))
            for hpo_id, hpo_label in selected:
                if (hpo_id, hpo_label) not in existing:
                    idx = self.pheno_list.InsertItem(self.pheno_list.GetItemCount(), hpo_id)
                    self.pheno_list.SetItem(idx, 1, hpo_label)
        dlg.Destroy()

    def on_remove_pheno(self, event):
        selected = []
        idx = self.pheno_list.GetFirstSelected()
        while idx != -1:
            selected.append(idx)
            idx = self.pheno_list.GetNextSelected(idx)
        for i in reversed(selected):
            self.pheno_list.DeleteItem(i)

    def on_copy_hpos(self, event):
        # Gather all HPO terms from the pheno_list
        hpo_lines = []
        for i in range(self.pheno_list.GetItemCount()):
            hpo_id = self.pheno_list.GetItemText(i)
            hpo_label = self.pheno_list.GetItem(i, 1).GetText()
            if hpo_id and hpo_label:
                hpo_lines.append(f"{hpo_id}\t{hpo_label}")
        if hpo_lines:
            # Join lines and copy to clipboard
            clipboard_text = "\n".join(hpo_lines)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(clipboard_text))
                wx.TheClipboard.Close()
                wx.MessageBox("HPO terms copied to clipboard.", "Copied", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox("Could not open the clipboard.", "Clipboard Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("No HPO terms to copy.", "Info", wx.OK | wx.ICON_INFORMATION)


    def on_save(self, event):
        # Update JSON data from fields



        dob_input = self.subject_dob.GetValue().strip()
        if dob_input:
            try:
                # Parse according to your expected format, e.g., YYYY-MM-DD
                import datetime
                dob = datetime.datetime.strptime(dob_input, "%Y-%m-%d")
                dob_str = dob.strftime("%Y-%m-%dT00:00:00Z")  # Save in ISO format with time and timezone
            except ValueError:
                dob_str = ""  # Or handle invalid input appropriately
        else:
            dob_str = ""



        self.json_data['subject'] = {
            'id': self.subject_id.GetValue(),
            'sex': self.subject_sex.GetStringSelection(),
            'karyotypic_sex': self.karyotype_choice.GetStringSelection(),
            'date_of_birth': dob_str
        }






        # Phenotypic features
        features = []
        for i in range(self.pheno_list.GetItemCount()):
            hpo_id = self.pheno_list.GetItemText(i)
            hpo_label = self.pheno_list.GetItem(i, 1).GetText()
            if hpo_id and hpo_label:
                features.append({'type': {'id': hpo_id, 'label': hpo_label}})
        self.json_data['phenotypicFeatures'] = features
        if 'metaData' not in self.json_data:
            self.json_data['metaData'] = {}
        self.json_data['metaData']['createdBy'] = self.created_by.GetValue()

        # Protobuf validation
        try:
            json_str = json.dumps(self.json_data)
            phenopacket = Parse(json_str, Phenopacket())  # noqa: F841
        except ParseError as e:
            wx.MessageBox(f"Validation error: {e}", "Invalid Phenopacket", wx.OK | wx.ICON_ERROR)
            return

        # Save to file if valid
        if self.file_path:
            with open(self.file_path, 'w') as f:
                json.dump(self.json_data, f, indent=2)
            wx.MessageBox("File saved!", "Success", wx.OK | wx.ICON_INFORMATION)

if __name__ == '__main__':
    app = wx.App(False)
    frame = PhenopacketEditor(None, "Phenopacket JSON Editor")
    frame.Show()
    app.MainLoop()
