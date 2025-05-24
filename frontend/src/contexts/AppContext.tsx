import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  uploaded: boolean;
}

interface JobStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  message?: string;
  conclusion?: string;
}

interface JobSummary {
  case_overview: {
    files_analyzed: number;
    document_types: string[];
    total_characters: number;
  };
  analysis_metrics: {
    total_nodes_created: number;
    analysis_depth: number;
    tasks_completed: number;
    tasks_failed: number;
  };
  key_findings: string[];
  evidence_summary: Array<{
    type: string;
    description: string;
  }>;
  conclusion: string;
  case_status: string;
  investigation_confidence?: number; // Added for confidence score
  suspect_analysis?: Array<{
    type: string;
    subject: string;
    analysis: string;
  }>; // Added for suspect analysis
  timeline_reconstruction?: Array<{
    event: string;
    details: string;
    source: string;
  }>; // Added for timeline
  ai_insights?: string[]; // Added for AI insights
  next_steps?: string[]; // Added for next steps
}

interface CompletedJob {
  id: string;
  name: string;
  completedAt: string;
  summary: JobSummary;
  status: 'completed' | 'error';
}

interface AppContextType {
  uploadedFiles: UploadedFile[];
  setUploadedFiles: React.Dispatch<React.SetStateAction<UploadedFile[]>>;
  jobStatus: JobStatus;
  setJobStatus: React.Dispatch<React.SetStateAction<JobStatus>>;
  jobSummary: JobSummary | null;
  setJobSummary: React.Dispatch<React.SetStateAction<JobSummary | null>>;
  currentJobName: string;
  setCurrentJobName: React.Dispatch<React.SetStateAction<string>>;
  jobHistory: CompletedJob[];
  setJobHistory: React.Dispatch<React.SetStateAction<CompletedJob[]>>;
  uploading: boolean;
  setUploading: React.Dispatch<React.SetStateAction<boolean>>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [jobStatus, setJobStatus] = useState<JobStatus>({ status: 'idle' });
  const [jobSummary, setJobSummary] = useState<JobSummary | null>(null);
  const [currentJobName, setCurrentJobName] = useState<string>('');
  const [jobHistory, setJobHistory] = useState<CompletedJob[]>([]);
  const [uploading, setUploading] = useState(false);

  const value = {
    uploadedFiles,
    setUploadedFiles,
    jobStatus,
    setJobStatus,
    jobSummary,
    setJobSummary,
    currentJobName,
    setCurrentJobName,
    jobHistory,
    setJobHistory,
    uploading,
    setUploading,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export type { UploadedFile, JobStatus, JobSummary, CompletedJob }; 