"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { api, getAuthHeaders } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";

export function InsuranceDetail({ insurance, onClose, onUpdate }: any) {
  const [documents, setDocuments] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState(insurance);

  useEffect(() => {
    loadDocuments();
  }, [insurance.id]);

  const loadDocuments = async () => {
    try {
      const data = await api.get(`/documents/insurance/${insurance.id}`);
      setDocuments(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdate = async () => {
    try {
      await api.put(`/insurances/${insurance.id}`, formData);
      setEditMode(false);
      onUpdate();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDownload = async (docId: string, filename: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    try {
      const res = await fetch(`/api/documents/${docId}/download`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[800px] bg-zinc-950 border-zinc-800 text-zinc-50 max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl text-indigo-400">{insurance.name}</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="details" className="w-full mt-4">
          <TabsList className="bg-zinc-900 border border-zinc-800">
            <TabsTrigger value="details">Details & Daten</TabsTrigger>
            <TabsTrigger value="documents">Dokumente ({documents.length})</TabsTrigger>
          </TabsList>
          
          <TabsContent value="details" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <span className="text-xs text-zinc-500 uppercase">Gesellschaft</span>
                {editMode ? 
                  <Input value={formData.company || ""} onChange={e => setFormData({...formData, company: e.target.value})} className="bg-zinc-900 border-zinc-700" />
                  : <p className="font-medium">{insurance.company || "-"}</p>
                }
              </div>
              <div className="space-y-1">
                <span className="text-xs text-zinc-500 uppercase">Versicherungs-Nr.</span>
                {editMode ? 
                  <Input value={formData.insurance_number || ""} onChange={e => setFormData({...formData, insurance_number: e.target.value})} className="bg-zinc-900 border-zinc-700" />
                  : <p className="font-medium">{insurance.insurance_number || "-"}</p>
                }
              </div>
              <div className="space-y-1">
                <span className="text-xs text-zinc-500 uppercase">Beginn</span>
                {editMode ? 
                  <Input type="date" value={formData.start_date || ""} onChange={e => setFormData({...formData, start_date: e.target.value})} className="bg-zinc-900 border-zinc-700" />
                  : <p className="font-medium">{insurance.start_date || "-"}</p>
                }
              </div>
              <div className="space-y-1">
                <span className="text-xs text-zinc-500 uppercase">Ende</span>
                {editMode ? 
                  <Input type="date" value={formData.end_date || ""} onChange={e => setFormData({...formData, end_date: e.target.value})} className="bg-zinc-900 border-zinc-700" />
                  : <p className="font-medium">{insurance.end_date || "-"}</p>
                }
              </div>
              <div className="space-y-1 col-span-2">
                <span className="text-xs text-indigo-400 uppercase font-semibold">Kündbar bis</span>
                {editMode ? 
                  <Input type="date" value={formData.cancellation_date || ""} onChange={e => setFormData({...formData, cancellation_date: e.target.value})} className="bg-zinc-900 border-zinc-700 text-indigo-400" />
                  : <p className="font-medium text-indigo-300">{insurance.cancellation_date || "-"}</p>
                }
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              {editMode ? (
                <>
                  <Button variant="outline" onClick={() => setEditMode(false)} className="border-zinc-700">Abbrechen</Button>
                  <Button onClick={handleUpdate} className="bg-indigo-600 hover:bg-indigo-700">Speichern</Button>
                </>
              ) : (
                <Button onClick={() => setEditMode(true)} variant="secondary" className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300">Bearbeiten</Button>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="documents" className="mt-4">
            <div className="border border-zinc-800 rounded-md bg-zinc-900/50">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-zinc-800/50">
                    <TableHead className="text-zinc-400">Dateiname</TableHead>
                    <TableHead className="text-zinc-400">Upload-Datum</TableHead>
                    <TableHead className="text-right text-zinc-400">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc: any) => (
                    <TableRow key={doc.id} className="border-zinc-800 hover:bg-zinc-800/50">
                      <TableCell className="font-medium">{doc.original_filename}</TableCell>
                      <TableCell>{new Date(doc.upload_date).toLocaleDateString("de-DE")}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="ghost" className="text-indigo-400 hover:text-indigo-300 hover:bg-indigo-400/10" onClick={() => handleDownload(doc.id, doc.original_filename)}>
                          Download
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {documents.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-zinc-500 py-6">Keine Dokumente vorhanden.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
