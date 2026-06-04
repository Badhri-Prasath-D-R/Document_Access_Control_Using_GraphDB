import React, { useState, useEffect } from 'react';
import { 
  FileText, Search, ShieldCheck, Download, Edit3, Eye, 
  Terminal, RefreshCw, Key, FolderOpen, AlertCircle,
  ChevronDown, ChevronRight, Folder
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [psno, setPsno] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [perfMetrics, setPerfMetrics] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50;

  const [selectedDocId, setSelectedDocId] = useState(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  
  const [editDoc, setEditDoc] = useState(null);
  const [editPayload, setEditPayload] = useState('');

  const [expandedGroups, setExpandedGroups] = useState({});

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, roleFilter]);

  const fetchUserPermissions = async (targetPsno) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/getDocumentIDAndAccess/${targetPsno}`);
      if (!response.ok) throw new Error(`Server returned error status: ${response.status}`);
      
      const data = await response.json();
      setDocuments(data.accessible_documents || []);
      setPerfMetrics({
        qtime: data.qtimeTaken,
        atime: data.atimeTaken,
        totalDocs: data.total_accessible_documents
      });
      setIsAuthenticated(true);
    } catch (err) {
      setError(err.message || "Failed to establish a line to the clearance database.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    if (psno.trim()) {
      fetchUserPermissions(psno.trim());
    }
  };

  const fetchFileBlob = async (docId, roleCode) => {
    const response = await fetch(`${API_BASE_URL}/api/documents/download/${docId}`, {
      method: 'GET',
      headers: {
        'X-PSNo': psno,
        'X-Role-Code': roleCode
      }
    });

    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || "Access Denied by verification firewall.");
    }

    return await response.blob();
  };

  const handleSecureDownload = async (docId, roleCode) => {
    try {
      const blob = await fetchFileBlob(docId, roleCode);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `Document_${docId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert(`Download Refused: ${err.message}`);
    }
  };

  useEffect(() => {
    if (!selectedDocId) {
      if (previewBlobUrl) window.URL.revokeObjectURL(previewBlobUrl);
      setPreviewBlobUrl(null);
      setPreviewError('');
      return;
    }

    const loadInlinePreview = async () => {
      setPreviewLoading(true);
      setPreviewError('');
      
      if (previewBlobUrl) {
        window.URL.revokeObjectURL(previewBlobUrl);
        setPreviewBlobUrl(null);
      }

      try {
        const matchingDoc = documents.find(d => d.DocumentID === selectedDocId);
        if (!matchingDoc) throw new Error("Document meta parameters mismatch.");

        const blob = await fetchFileBlob(selectedDocId, matchingDoc.AuthorizedByRoleCode);
        const safeUrl = window.URL.createObjectURL(blob);
        setPreviewBlobUrl(safeUrl);
      } catch (err) {
        setPreviewError(err.message);
      } finally {
        setPreviewLoading(false);
      }
    };

    loadInlinePreview();

    return () => {
      if (previewBlobUrl) window.URL.revokeObjectURL(previewBlobUrl);
    };
  }, [selectedDocId]);

  const handleModifyAsset = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/edit/${editDoc.DocumentID}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-PSNo': psno,
          'X-Role-Code': editDoc.AuthorizedByRoleCode
        },
        body: JSON.stringify({ update_data: { modificationPayload: editPayload } })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail);
      }

      alert(`Success: Document ${editDoc.DocumentID} properties modified successfully.`);
      setEditDoc(null);
      setEditPayload('');
    } catch (err) {
      alert(`Modification Refused: ${err.message}`);
    }
  };

  const handleDisconnect = () => {
    setIsAuthenticated(false);
    setDocuments([]);
    setPerfMetrics(null);
    setPsno('');
    setSelectedDocId(null);
    setExpandedGroups({});
  };

  const toggleGroupExpansion = (jobCode) => {
    setExpandedGroups(prev => ({
      ...prev,
      [jobCode]: !prev[jobCode]
    }));
  };

  const filteredDocs = documents.filter(doc => {
    const titleString = String(doc.DocumentTitle || "").toLowerCase();
    const idString = String(doc.DocumentID || "");
    const currentSearch = searchQuery.toLowerCase();

    const matchesSearch = titleString.includes(currentSearch) || idString.includes(currentSearch);
    const matchesRole = roleFilter === 'all' || String(doc.AuthorizedByRoleCode) === String(roleFilter);
    
    return matchesSearch && matchesRole;
  });

  const totalPages = Math.ceil(filteredDocs.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedDocs = filteredDocs.slice(startIndex, startIndex + itemsPerPage);

  const groupedDocuments = filteredDocs.reduce((acc, doc) => {
    const groupKey = doc.JobCode || "UNKNOWN_ROLE";
    if (!acc[groupKey]) {
      acc[groupKey] = [];
    }
    acc[groupKey].push(doc);
    return acc;
  }, {});

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-vault-bg p-4 text-slate-100">
        <div className="w-full max-w-md rounded-2xl border border-white/10 bg-vault-card p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <Terminal size={28} />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Document access</h2>
              <p className="text-xs text-slate-400">Secure Document Access Portal</p>
            </div>
          </div>

          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Employee PSNo Identifier</label>
              <div className="relative">
                <input 
                  type="text" 
                  className="w-full rounded-lg border border-white/10 bg-black/20 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 outline-hidden transition focus:border-blue-500 focus:bg-black/40" 
                  placeholder="Enter employee PSNo" 
                  value={psno}
                  onChange={(e) => setPsno(e.target.value)}
                  required
                />
                <Key className="absolute top-3 left-3.5 text-slate-500" size={16} />
              </div>
            </div>

            {error && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
                {error}
              </div>
            )}

            <button 
              type="submit" 
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-500 active:scale-98 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="animate-spin" size={16} /> : "Establish Access"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen bg-vault-bg text-slate-100 overflow-hidden font-sans">
      
      {/* 1. LEFT DIRECTORY PANEL - REFACTORED TO ACCORDION FOLDER STRUCTURE */}
      <div className="flex w-80 flex-col border-r border-white/10 bg-slate-950/60 backdrop-blur-xl shrink-0">
        <div className="flex items-center justify-between border-b border-white/5 p-4 bg-white/2">
          <div className="flex items-center gap-2 text-blue-400">
            <ShieldCheck size={20} />
            <span className="font-mono text-xs font-bold uppercase tracking-widest text-slate-300">Active Session</span>
          </div>
          <button 
            onClick={handleDisconnect}
            className="rounded-md border border-white/10 px-2 py-1 text-2xs font-medium text-red-400 transition hover:bg-red-500/10"
          >
            Disconnect
          </button>
        </div>

        <div className="p-4 bg-linear-to-b from-white/5 to-transparent border-b border-white/5">
          <div className="text-sm font-bold text-white">Operational Account</div>
          <div className="font-mono text-xs text-slate-400 mt-0.5">PSNo Reference: {psno}</div>

          {perfMetrics && (
            <div className="mt-3 space-y-1 rounded-lg bg-black/40 p-2 font-mono text-3xs text-emerald-400 border border-emerald-500/10">
              <div>• DB Query Execution: {perfMetrics.qtime.toFixed(4)}s</div>
              <div>• Pipe Processing Array: {perfMetrics.atime.toFixed(4)}s</div>
              <div>• Cache Node Volume: {perfMetrics.totalDocs} items</div>
            </div>
          )}
        </div>

        <div className="p-3 space-y-2.5 border-b border-white/5">
          <div className="relative">
            <input 
              type="text"
              placeholder="Filter list by title/ID..."
              className="w-full rounded-md border border-white/5 bg-black/30 py-1.5 pl-8 pr-3 text-xs text-white outline-hidden focus:border-blue-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search className="absolute top-2.5 left-2.5 text-slate-500" size={13} />
          </div>

          <div className="flex rounded-md bg-black/30 p-0.5 text-2xs border border-white/5">
            {['all', '5267', '5268'].map((type) => (
              <button
                key={type}
                onClick={() => setRoleFilter(type)}
                className={`flex-1 rounded-sm py-1 font-medium capitalize transition ${roleFilter === type ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              >
                {type === 'all' ? 'All' : type === '5267' ? 'Admin' : 'Viewer'}
              </button>
            ))}
          </div>
        </div>

        {/* CASCADING FOLDER VIEW ACCORDION TREE */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1 pt-2 select-none">
          <div className="px-2 py-1 text-3xs font-bold tracking-wider text-slate-500 uppercase mb-1">Clearance Map Directory</div>
          
          {Object.keys(groupedDocuments).length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 font-mono">No clearance assets found</div>
          ) : (
            Object.keys(groupedDocuments).map((jobCode) => {
              const isGroupExpanded = !!expandedGroups[jobCode];
              const groupFiles = groupedDocuments[jobCode];

              return (
                <div key={jobCode} className="border border-white/5 rounded-md bg-white/1 overflow-hidden">
                  
                  {/* Job Code Accordion Header Toggle Row */}
                  <button
                    onClick={() => toggleGroupExpansion(jobCode)}
                    className="w-full flex items-center justify-between p-2.5 text-left bg-slate-900/40 hover:bg-slate-900/90 transition-colors border-b border-white/5"
                  >
                    <div className="flex items-center gap-2 overflow-hidden mr-1">
                      {isGroupExpanded ? <ChevronDown size={12} className="text-slate-500 shrink-0" /> : <ChevronRight size={12} className="text-slate-500 shrink-0" />}
                      <Folder size={14} className="text-blue-500 shrink-0" />
                      <span className="font-mono text-3xs font-bold text-slate-300 truncate tracking-wide">
                        {jobCode}
                      </span>
                    </div>
                    <span className="font-mono text-4xs bg-slate-800 text-slate-400 font-bold px-1.5 py-0.5 rounded-sm shrink-0">
                      {groupFiles.length}
                    </span>
                  </button>

                  {/* Document Leaf Nodes List */}
                  {isGroupExpanded && (
                    <div className="bg-black/20 p-1 space-y-0.5 border-t border-white/5">
                      {groupFiles.map((doc) => (
                        <div 
                          key={doc.DocumentID} 
                          onClick={() => setSelectedDocId(doc.DocumentID)}
                          className={`group flex items-center justify-between rounded-sm px-2 py-1.5 text-xs transition cursor-pointer ${selectedDocId === doc.DocumentID ? 'bg-blue-600/20 border border-blue-500/20 text-white' : 'border border-transparent hover:bg-white/5 text-slate-400 hover:text-slate-200'}`}
                        >
                          <div className="flex items-center gap-2 overflow-hidden mr-2">
                            <FileText size={12} className={selectedDocId === doc.DocumentID ? 'text-blue-400' : 'text-slate-500'} />
                            <span className="truncate text-3xs">{doc.DocumentTitle}</span>
                          </div>
                          <span className={`font-mono text-4xs px-1 rounded-sm border ${doc.AuthorizedByRoleCode === '5267' ? 'text-amber-400 bg-amber-500/5 border-amber-500/20' : 'text-blue-400 bg-blue-500/5 border-blue-500/20'}`}>
                            {doc.AuthorizedByRoleCode === '5267' ? 'MDF' : 'VW'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 2. MIDDLE MAIN DATA MATRIX GRID PANEL */}
      <div className="flex flex-1 flex-col overflow-hidden bg-slate-900/40 border-r border-white/10">
        <div className="flex h-12 items-center justify-between border-b border-white/5 px-6 bg-slate-950/20 shrink-0">
          <h1 className="text-sm font-bold tracking-wide text-white font-mono">
            Document Access Matrix
          </h1>
          <div className="text-3xs font-mono text-slate-400">
            Showing {filteredDocs.length === 0 ? 0 : startIndex + 1} - {Math.min(startIndex + itemsPerPage, filteredDocs.length)} of {filteredDocs.length} entries
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div className="rounded-xl border border-white/5 bg-vault-card/40 shadow-xl overflow-hidden backdrop-blur-md">
            <table className="w-full border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-white/2 font-mono text-slate-400 text-3xs uppercase tracking-wider">
                  <th className="p-3">Asset ID</th>
                  <th className="p-3">Job Code</th>
                  <th className="p-3">Document Title</th>
                  <th className="p-3 text-right">Access Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono">
                {paginatedDocs.map((doc) => {
                  const isAdmin = doc.AuthorizedByRoleCode === "5267";
                  const isViewer = doc.AuthorizedByRoleCode === "5268";

                  return (
                    <tr 
                      key={doc.DocumentID} 
                      className={`hover:bg-white/1 cursor-pointer transition ${selectedDocId === doc.DocumentID ? 'bg-white/2' : ''}`}
                      onClick={() => setSelectedDocId(doc.DocumentID)}
                    >
                      <td className="p-3 font-bold text-slate-300">#{doc.DocumentID}</td>
                      <td className="p-3 text-blue-400 font-semibold">{doc.JobCode || '—'}</td>
                      <td className="p-3 text-slate-400 truncate max-w-[140px]">{doc.DocumentTitle}</td>
                      <td className="p-3 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                        <button 
                          onClick={() => setSelectedDocId(doc.DocumentID)}
                          className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-3xs font-semibold text-slate-300 hover:bg-slate-700 transition"
                        >
                          <Eye size={11} /> View
                        </button>
                        
                        <button 
                          disabled={isViewer}
                          onClick={() => handleSecureDownload(doc.DocumentID, doc.AuthorizedByRoleCode)}
                          className={`inline-flex items-center gap-1 rounded px-2 py-1 text-3xs font-semibold text-white transition ${isViewer ? 'bg-slate-950 text-slate-600 border border-white/5 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-500'}`}
                        >
                          <Download size={11} />
                        </button>

                        {isAdmin && (
                          <button 
                            onClick={() => { setEditDoc(doc); setEditPayload(''); }}
                            className="inline-flex items-center gap-1 rounded bg-amber-600 px-2 py-1 text-3xs font-semibold text-white hover:bg-amber-500 transition"
                          >
                            <Edit3 size={11} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {totalPages > 1 && (
          <div className="flex h-12 items-center justify-between border-t border-white/5 px-4 bg-slate-950/40 shrink-0 font-mono text-3xs">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              className="rounded border border-white/10 px-3 py-1 text-slate-300 transition hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent"
            >
              &lt;&lt; PREV_PAGE
            </button>
            
            <span className="text-slate-500">
              PAGE <span className="text-blue-400 font-bold">{currentPage}</span> OF {totalPages}
            </span>

            <button
              type="button"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              className="rounded border border-white/10 px-3 py-1 text-slate-300 transition hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent"
            >
              NEXT_PAGE &gt;&gt;
            </button>
          </div>
        )}
      </div>

      {/* 3. RIGHT PANEL - LIVE PDF VIEW STREAM WINDOW */}
      <div className="flex w-1/2 flex-col overflow-hidden bg-slate-950/90 backdrop-blur-sm shrink-0">
        <div className="flex h-12 items-center justify-between border-b border-white/5 px-4 bg-slate-950/40 shrink-0">
          <div className="text-xs font-bold font-mono text-slate-300 flex items-center gap-2">
            <Terminal size={14} className="text-blue-400" />
            <span>FILE_PREVIEW_PANE {selectedDocId ? `[ASSET #${selectedDocId}]` : ''}</span>
          </div>
          {selectedDocId && (
            <button 
              onClick={() => setSelectedDocId(null)}
              className="text-3xs font-semibold text-red-400 hover:text-red-300"
            >
              Clear View
            </button>
          )}
        </div>

        <div className="flex-1 bg-slate-950 flex items-center justify-center relative">
          {previewLoading ? (
            <div className="text-center font-mono space-y-2">
              <RefreshCw className="animate-spin text-blue-500 mx-auto" size={24} />
              <p className="text-3xs text-slate-500">Decrypting file buffer stream...</p>
            </div>
          ) : previewError ? (
            <div className="text-center font-mono space-y-3 p-6 max-w-xs text-red-400">
              <AlertCircle className="mx-auto" size={32} />
              <h3 className="text-xs font-bold">Preview Authorization Failed</h3>
              <p className="text-3xs text-slate-500">{previewError}</p>
            </div>
          ) : previewBlobUrl ? (
            <object
              data={previewBlobUrl}
              type="application/pdf"
              className="w-full h-full border-none"
            >
              <embed src={previewBlobUrl} type="application/pdf" className="w-full h-full" />
            </object>
          ) : (
            <div className="text-center text-slate-500 font-mono space-y-2 p-6">
              <FolderOpen size={48} className="mx-auto text-slate-600 animate-pulse" />
              <h3 className="text-xs font-bold text-slate-400">No Target Active</h3>
              <p className="text-3xs text-slate-500 max-w-xs">Select a file from the side bar directory or data table to open secure preview frames.</p>
            </div>
          )}
        </div>
      </div>

      {/* 4. METADATA RE-CONFIGURATION MODAL (ADMIN CONTROL PANEL) */}
      {editDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-sm font-bold font-mono text-white mb-1 flex items-center gap-2">
              <Edit3 size={16} className="text-amber-500" />
              <span>Modify Document Metadata Context</span>
            </h3>
            <p className="text-2xs text-slate-400 font-mono mb-4">Target Node ID: #{editDoc.DocumentID}</p>
            
            <form onSubmit={handleModifyAsset} className="space-y-4">
              <div>
                <label className="block text-3xs font-mono uppercase tracking-wider text-slate-500 mb-1">Configuration Changes (JSON/Text)</label>
                <textarea
                  rows={4}
                  className="w-full rounded-md border border-white/15 bg-black/40 p-2 font-mono text-xs text-white outline-hidden focus:border-amber-500"
                  placeholder='{"title": "Updated configuration properties"}'
                  value={editPayload}
                  onChange={(e) => setEditPayload(e.target.value)}
                  required
                />
              </div>

              <div className="flex justify-end gap-2 text-2xs font-semibold">
                <button 
                  type="button" 
                  onClick={() => setEditDoc(null)}
                  className="rounded bg-white/5 px-3 py-1.5 text-slate-300 hover:bg-white/10"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="rounded bg-amber-600 px-3 py-1.5 text-white hover:bg-amber-500"
                >
                  Commit Modifications
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;