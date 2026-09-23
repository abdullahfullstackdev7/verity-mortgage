import { useState } from 'react'
import { FileText, ScanSearch, Upload } from 'lucide-react'

import { OcrStatusBadge } from '@/components/app/Badges'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { extractDocument, fetchDocumentFileUrl, listExtractedFields, uploadDocument } from '@/lib/api'
import type { DocumentRecord, DocumentType, ExtractedField } from '@/lib/types'

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  paystub: 'Pay Stub',
  bank_statement: 'Bank Statement',
  w2: 'W-2',
  id: 'ID',
}

export function DocumentsPanel({
  caseId,
  documents,
  canUpload,
  canExtract,
  onDocumentsChanged,
}: {
  caseId: string
  documents: DocumentRecord[]
  canUpload: boolean
  canExtract: boolean
  onDocumentsChanged: () => void
}) {
  const [docType, setDocType] = useState<DocumentType>('paystub')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [extractingId, setExtractingId] = useState<string | null>(null)
  const [fieldsByDoc, setFieldsByDoc] = useState<Record<string, ExtractedField[]>>({})
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null)
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({})
  const [previewingId, setPreviewingId] = useState<string | null>(null)

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setUploadError(null)
    try {
      await uploadDocument(caseId, docType, file)
      setFile(null)
      onDocumentsChanged()
    } catch {
      setUploadError('Upload failed. Only genuine PDF files are accepted.')
    } finally {
      setUploading(false)
    }
  }

  async function handleExtract(documentId: string) {
    setExtractingId(documentId)
    try {
      const fields = await extractDocument(caseId, documentId)
      setFieldsByDoc((prev) => ({ ...prev, [documentId]: fields }))
      setExpandedDoc(documentId)
      onDocumentsChanged()
    } finally {
      setExtractingId(null)
    }
  }

  async function toggleFields(documentId: string) {
    if (expandedDoc === documentId) {
      setExpandedDoc(null)
      return
    }
    if (!fieldsByDoc[documentId]) {
      const fields = await listExtractedFields(caseId, documentId)
      setFieldsByDoc((prev) => ({ ...prev, [documentId]: fields }))
    }
    setExpandedDoc(documentId)
  }

  async function handlePreview(documentId: string) {
    setPreviewingId(documentId)
    try {
      if (!previewUrls[documentId]) {
        const url = await fetchDocumentFileUrl(caseId, documentId)
        setPreviewUrls((prev) => ({ ...prev, [documentId]: url }))
      }
    } finally {
      setPreviewingId(null)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <h2 className="text-lg font-semibold text-foreground">Documents</h2>

      {canUpload ? (
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg bg-secondary/40 p-4">
          <div className="w-40">
            <Select value={docType} onValueChange={(v) => setDocType(v as DocumentType)}>
              <SelectTrigger>
                <SelectValue>{(value: DocumentType) => DOC_TYPE_LABELS[value]}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="paystub">Pay Stub</SelectItem>
                <SelectItem value="bank_statement">Bank Statement</SelectItem>
                <SelectItem value="w2">W-2</SelectItem>
                <SelectItem value="id">ID</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="flex-1 text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium"
          />
          <Button onClick={handleUpload} disabled={!file || uploading}>
            <Upload className="size-4" />
            {uploading ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      ) : null}
      {uploadError ? <p className="mt-2 text-sm text-destructive">{uploadError}</p> : null}

      <div className="mt-4 space-y-3">
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
        ) : (
          documents.map((doc) => (
            <div key={doc.id} className="rounded-lg border border-border">
              <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-3">
                  <FileText className="size-5 text-muted-foreground" strokeWidth={1.75} />
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {DOC_TYPE_LABELS[doc.doc_type]}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Uploaded {new Date(doc.uploaded_at).toLocaleString()}
                    </p>
                  </div>
                  <OcrStatusBadge status={doc.ocr_status} />
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => handlePreview(doc.id)} disabled={previewingId === doc.id}>
                    {previewingId === doc.id ? 'Loading…' : 'Preview'}
                  </Button>
                  {canExtract ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExtract(doc.id)}
                      disabled={extractingId === doc.id}
                    >
                      <ScanSearch className="size-4" />
                      {extractingId === doc.id ? 'Extracting…' : 'Extract'}
                    </Button>
                  ) : null}
                  {doc.ocr_status === 'completed' ? (
                    <Button variant="ghost" size="sm" onClick={() => toggleFields(doc.id)}>
                      {expandedDoc === doc.id ? 'Hide fields' : 'View fields'}
                    </Button>
                  ) : null}
                </div>
              </div>

              {previewUrls[doc.id] ? (
                <iframe
                  title={`${doc.doc_type} preview`}
                  src={previewUrls[doc.id]}
                  className="h-96 w-full border-t border-border"
                />
              ) : null}

              {expandedDoc === doc.id ? (
                <div className="border-t border-border p-4">
                  {(fieldsByDoc[doc.id] ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No extracted fields yet.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <tbody>
                        {fieldsByDoc[doc.id].map((field) => (
                          <tr key={field.id} className="border-b border-border/60 last:border-0">
                            <td className="py-1.5 pr-4 font-medium text-foreground">
                              {field.field_name}
                            </td>
                            <td className="py-1.5 pr-4 text-muted-foreground">
                              {field.extracted_value}
                            </td>
                            <td className="py-1.5 text-xs text-muted-foreground">
                              {field.confidence_score !== null
                                ? `${Math.round(field.confidence_score * 100)}% confidence`
                                : ''}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
