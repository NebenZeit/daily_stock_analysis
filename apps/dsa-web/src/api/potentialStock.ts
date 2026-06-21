import apiClient from './index';
import { toCamelCase } from './utils';

export type ScreeningResultItem = {
  id: string;
  stockCode: string;
  stockName: string;
  eventType: string;
  signalPriority: string;
  announcementTitle: string;
  fundamentalScore: number;
  industryScore: number;
  compositeRating: number;
  ratingLevel: string;
  createdAt: string;
  trackedStatus?: string | null;
};

export type ScreeningResultList = {
  items: ScreeningResultItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type ScreeningResultDetail = {
  id: string;
  stockCode: string;
  stockName: string;
  eventType: string;
  signalPriority: string;
  announcementTitle: string;
  fundamentalScore: number;
  fundamentalDetail: Record<string, unknown>;
  industryScore: number;
  industryDetail: Record<string, unknown>;
  compositeRating: number;
  ratingLevel: string;
  pseudoSignals: Array<{ type: string; severity: string; reason: string }>;
  reportMd: string;
  createdAt: string;
};

export type ScanTaskInfo = {
  id: string;
  triggerType: string;
  status: string;
  startedAt?: string | null;
  completedAt?: string | null;
  scanFrom: string;
  scanTo: string;
  announcementsFetched: number;
  signalsMatched: number;
  resultsProduced: number;
  taskMeta?: { announcements?: AnnouncementInfo[] } | null;
};

export type TrackedTarget = {
  id: string;
  stockCode: string;
  stockName: string;
  status: string;
  addedAt: string;
  updatedAt: string;
  removedReason?: string | null;
  notes?: string | null;
};

export type AnnouncementInfo = {
  id: string;
  stockCode: string;
  stockName: string;
  title: string;
  publishTime: string;
  eventType: string;
  signalPriority: string;
  status: string;
};

export type ScanResponse = {
  taskId: string;
  status: string;
  message: string;
  resultsProduced: number;
  announcementsFetched: number;
  signalsMatched: number;
  hasDetails: boolean;
  boardType?: string;
};

export type ScanTaskDetail = {
  id: string;
  triggerType: string;
  status: string;
  startedAt: string | null;
  completedAt: string | null;
  scanFrom: string;
  scanTo: string;
  announcementsFetched: number;
  signalsMatched: number;
  resultsProduced: number;
  errorLog: string | null;
  taskMeta?: { announcements?: AnnouncementInfo[] } | null;
};

export type ScanRequest = {
  since?: string;
  until?: string;
  targetStocks?: string[];
  sector?: string;
  boardType?: string;
};

export const potentialStockApi = {
  async triggerScan(payload: ScanRequest): Promise<ScanResponse> {
    const resp = await apiClient.post<Record<string, unknown>>('/api/v1/potential-stock/scan', {
      since: payload.since,
      until: payload.until,
      target_stocks: payload.targetStocks,
      sector: payload.sector,
      board_type: payload.boardType || 'main_board',
    });
    return toCamelCase<ScanResponse>(resp.data);
  },

  async listResults(params: {
    page?: number;
    pageSize?: number;
    eventType?: string;
    ratingLevel?: string;
    since?: string;
    until?: string;
    stockCode?: string;
  } = {}): Promise<ScreeningResultList> {
    const resp = await apiClient.get<Record<string, unknown>>('/api/v1/potential-stock/results', { params });
    return toCamelCase<ScreeningResultList>(resp.data);
  },

  async getResultDetail(id: string): Promise<ScreeningResultDetail> {
    const resp = await apiClient.get<Record<string, unknown>>(`/api/v1/potential-stock/results/${id}`);
    return toCamelCase<ScreeningResultDetail>(resp.data);
  },

  async listTasks(limit = 20): Promise<{ items: ScanTaskInfo[]; total: number }> {
    const resp = await apiClient.get<Record<string, unknown>>('/api/v1/potential-stock/tasks', { params: { limit } });
    return toCamelCase<{ items: ScanTaskInfo[]; total: number }>(resp.data);
  },

  async getTask(id: string): Promise<ScanTaskDetail> {
    const resp = await apiClient.get<Record<string, unknown>>(`/api/v1/potential-stock/tasks/${id}`);
    return toCamelCase<ScanTaskDetail>(resp.data);
  },

  async listTargets(): Promise<{ items: TrackedTarget[]; total: number }> {
    const resp = await apiClient.get<Record<string, unknown>>('/api/v1/potential-stock/targets');
    return toCamelCase<{ items: TrackedTarget[]; total: number }>(resp.data);
  },

  async updateTargetStatus(stockCode: string, status: string, reason?: string): Promise<void> {
    await apiClient.put(`/api/v1/potential-stock/targets/${stockCode}/status`, {
      status,
      reason: reason || undefined,
    });
  },
};
