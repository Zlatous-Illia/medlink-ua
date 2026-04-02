import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { FileText, Download } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'

function formatFileSize(bytes?: number) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function MyDocumentsPage() {
  const { data: documents, isLoading, isError } = useQuery({
    queryKey: ['my-documents'],
    queryFn: () => cabinetApi.getDocuments().then(r => r.data),
    retry: false,
  })

  if (isLoading) return <PageLoading />
  if (isError) return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої документи</h1>
      <div className="card p-6 text-center text-gray-500">
        Профіль пацієнта не прив'язано до акаунту. Зверніться до адміністратора.
      </div>
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої документи</h1>

      {!documents?.length ? (
        <div className="card p-4">
          <EmptyState message="Документів не знайдено" />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Назва файлу</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Тип</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Розмір</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Дата</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} className="border-b border-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-gray-400" />
                      <span className="font-medium text-gray-900">{doc.file_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{doc.file_type ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{formatFileSize(doc.file_size)}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {format(new Date(doc.uploaded_at), 'dd.MM.yyyy')}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={doc.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-secondary btn-sm btn"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
