import React, { useCallback, useEffect, useState } from 'react';
import { AppPage } from '../components/common/AppPage';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import {
  potentialStockApi,
  type ScreeningResultItem,
  type ScanResponse,
  type ScanTaskInfo,
  type ScanTaskDetail,
  type AnnouncementInfo,
} from '../api/potentialStock';

const EVENT_LABELS: Record<string, string> = {
  M_A: '并购重组',
  CAP_EXPAND: '产能扩张',
  BIZ_CHANGE: '业务变更',
  TECH_COOP: '技术合作',
  ORDER: '订单落地',
};

const RATING_COLORS: Record<string, string> = {
  A: 'text-green-600 bg-green-50',
  B: 'text-blue-600 bg-blue-50',
  C: 'text-yellow-600 bg-yellow-50',
  D: 'text-gray-500 bg-gray-50',
};

const STATUS_LABELS: Record<string, string> = {
  COMPLETED: '已完成',
  RUNNING: '运行中',
  FAILED: '失败',
  PENDING: '等待中',
};

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: 'text-green-600 bg-green-50',
  RUNNING: 'text-blue-600 bg-blue-50',
  FAILED: 'text-red-600 bg-red-50',
  PENDING: 'text-gray-500 bg-gray-50',
};

const TRIGGER_LABELS: Record<string, string> = {
  MANUAL: '手动',
  SCHEDULED: '定时',
  INCREMENTAL: '增量',
};

/* ── Scan Summary Banner ────────────────────────── */

const ScanSummaryCard: React.FC<{
  summary: ScanResponse;
  announcements: AnnouncementInfo[];
  onViewAnnouncements: () => void;
}> = ({ summary, announcements, onViewAnnouncements }) => {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  const hasSignals = summary.signalsMatched > 0;
  const hasResults = summary.resultsProduced > 0;

  return (
    <Card className="border-l-4 border-l-blue-500">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-800">📊 扫描完成</h3>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[summary.status] || ''}`}>
              {STATUS_LABELS[summary.status] || summary.status}
            </span>
          </div>

          <div className="flex flex-wrap gap-4 text-sm text-gray-600">
            <span>获取公告 <strong className="text-gray-800">{summary.announcementsFetched}</strong> 条</span>
            {hasSignals ? (
              <span>命中信号 <strong className="text-green-600">{summary.signalsMatched}</strong> 条</span>
            ) : (
              <span>命中信号 <strong className="text-yellow-500">0</strong> 条</span>
            )}
            {hasResults && (
              <span>产出潜力标的 <strong className="text-orange-600">{summary.resultsProduced}</strong> 条</span>
            )}
          </div>

          {announcements.length > 0 && (
            <button
              className="text-xs text-blue-500 hover:underline"
              onClick={onViewAnnouncements}
            >
              查看全部 {announcements.length} 条公告详情 →
            </button>
          )}

          {!hasSignals && (
            <p className="text-xs text-yellow-600">
              ⚠️ 本次扫描未命中事件信号。可能是扫描范围内无匹配公告事件。
            </p>
          )}
        </div>

        <button
          className="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100"
          onClick={() => setDismissed(true)}
          title="关闭"
        >
          ✕
        </button>
      </div>
    </Card>
  );
};

/* ── Announcement Table ─────────────────────────── */

const AnnouncementRow: React.FC<{
  ann: AnnouncementInfo;
  index: number;
}> = ({ ann, index }) => {
  const isMatched = ann.status === 'SIGNAL_MATCHED';
  const eventLabel = EVENT_LABELS[ann.eventType] || ann.eventType;
  const dateStr = ann.publishTime ? ann.publishTime.slice(0, 10) : '';

  return (
    <tr className="border-b border-gray-50 transition-colors hover:bg-gray-50/50">
      <td className="px-4 py-2.5 text-xs text-gray-400">{index + 1}</td>
      <td className="px-4 py-2.5">
        <div className="text-sm font-medium text-gray-800">{ann.stockName}</div>
        <div className="text-xs text-gray-400">{ann.stockCode}</div>
      </td>
      <td className="max-w-xs truncate px-4 py-2.5 text-sm text-gray-700" title={ann.title}>
        {ann.title}
      </td>
      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-gray-400">{dateStr}</td>
      <td className="px-4 py-2.5">
        {isMatched ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
            已匹配 · {eventLabel}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
            未命中
          </span>
        )}
      </td>
    </tr>
  );
};

/* ── Task History ───────────────────────────────── */

const TaskRow: React.FC<{
  task: ScanTaskInfo;
  index: number;
  onViewDetail: (taskId: string) => void;
}> = ({ task, index, onViewDetail }) => {
  const dateStr = task.startedAt ? task.startedAt.slice(0, 16).replace('T', ' ') : '';
  const triggerLabel = TRIGGER_LABELS[task.triggerType] || task.triggerType;

  return (
    <tr className="border-b border-gray-50 transition-colors hover:bg-gray-50/50">
      <td className="px-3 py-2 text-xs text-gray-400">{index + 1}</td>
      <td className="px-3 py-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[task.status] || ''}`}>
          {STATUS_LABELS[task.status] || task.status}
        </span>
      </td>
      <td className="px-3 py-2 text-xs text-gray-500">{triggerLabel}</td>
      <td className="px-3 py-2 text-xs text-gray-500">{dateStr}</td>
      <td className="px-3 py-2 text-xs text-gray-600">{task.scanFrom} ~ {task.scanTo}</td>
      <td className="px-3 py-2 text-xs text-gray-600">{task.announcementsFetched}</td>
      <td className="px-3 py-2 text-xs text-gray-600">{task.signalsMatched}</td>
      <td className="px-3 py-2 text-xs text-gray-600">{task.resultsProduced}</td>
      <td className="px-3 py-2">
        <button
          className="text-xs text-blue-500 hover:underline"
          onClick={() => onViewDetail(task.id)}
        >
          详情
        </button>
      </td>
    </tr>
  );
};

/* ── Task Detail Modal ──────────────────────────── */

const TaskDetailModal: React.FC<{
  taskDetail: ScanTaskDetail;
  announcements: AnnouncementInfo[];
  onClose: () => void;
}> = ({ taskDetail, announcements, onClose }) => {
  const matchedAnnouncements = announcements.filter(a => a.status === 'SIGNAL_MATCHED');

  const boardType = taskDetail.taskMeta?.board_type || 'main_board';
  const boardLabel = boardType === 'all' ? '全市场（含创业板/科创板）' : '仅主板A股';

  const statusLabel = STATUS_LABELS[taskDetail.status] || taskDetail.status;
  const triggerLabel = TRIGGER_LABELS[taskDetail.triggerType] || taskDetail.triggerType;
  const startStr = taskDetail.startedAt ? taskDetail.startedAt.slice(0, 19).replace('T', ' ') : '-';
  const endStr = taskDetail.completedAt ? taskDetail.completedAt.slice(0, 19).replace('T', ' ') : '-';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="max-h-[85vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">扫描任务详情</h2>
          <button
            className="rounded px-3 py-1 text-sm text-gray-400 hover:bg-gray-100"
            onClick={onClose}
          >
            关闭
          </button>
        </div>

        {/* 任务概要 */}
        <div className="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-gray-50 p-4 text-sm">
          <div>
            <span className="text-gray-400">状态：</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[taskDetail.status] || ''}`}>
              {statusLabel}
            </span>
          </div>
          <div><span className="text-gray-400">触发方式：</span>{triggerLabel}</div>
          <div><span className="text-gray-400">板块过滤：</span>{boardLabel}</div>
          <div><span className="text-gray-400">扫描范围：</span>{taskDetail.scanFrom} ~ {taskDetail.scanTo}</div>
          <div><span className="text-gray-400">开始时间：</span>{startStr}</div>
          <div><span className="text-gray-400">结束时间：</span>{endStr}</div>
          {taskDetail.errorLog && (
            <div className="col-span-2">
              <span className="text-red-500">错误：</span>{taskDetail.errorLog}
            </div>
          )}
        </div>

        {/* 统计 */}
        <div className="mb-4 flex flex-wrap gap-6 text-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{taskDetail.announcementsFetched}</div>
            <div className="text-xs text-gray-400">获取公告</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{taskDetail.signalsMatched}</div>
            <div className="text-xs text-gray-400">命中信号</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{taskDetail.resultsProduced}</div>
            <div className="text-xs text-gray-400">产出标的</div>
          </div>
        </div>

        {/* 公告明细 */}
        {announcements.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-700">
              公告明细（{matchedAnnouncements.length} 条命中 / {announcements.length} 条总计）
            </h3>
            <div className="max-h-64 overflow-y-auto rounded border border-gray-100">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-gray-50">
                  <tr className="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <th className="px-3 py-2 font-medium">#</th>
                    <th className="px-3 py-2 font-medium">标的</th>
                    <th className="px-3 py-2 font-medium">公告标题</th>
                    <th className="px-3 py-2 font-medium">日期</th>
                    <th className="px-3 py-2 font-medium">信号</th>
                  </tr>
                </thead>
                <tbody>
                  {announcements.map((ann, i) => (
                    <AnnouncementRow key={ann.id} ann={ann} index={i} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!announcements.length && (
          <div className="py-8 text-center text-sm text-gray-400">该任务无公告明细数据。</div>
        )}
      </div>
    </div>
  );
};

/* ── Main Page ──────────────────────────────────── */

export const PotentialStockMiningPage: React.FC = () => {
  const [results, setResults] = useState<ScreeningResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ScreeningResultItem | null>(null);
  const [detailMd, setDetailMd] = useState<string>('');
  const [showDetail, setShowDetail] = useState(false);

  // Scan summary state
  const [scanSummary, setScanSummary] = useState<ScanResponse | null>(null);
  const [announcements, setAnnouncements] = useState<AnnouncementInfo[]>([]);
  const [showAnnouncements, setShowAnnouncements] = useState(false);

  // Task history state
  const [tasks, setTasks] = useState<ScanTaskInfo[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [showTaskHistory, setShowTaskHistory] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedTaskDetail, setSelectedTaskDetail] = useState<ScanTaskDetail | null>(null);
  const [selectedTaskAnnouncements, setSelectedTaskAnnouncements] = useState<AnnouncementInfo[]>([]);

  const pageSize = 20;

  const loadResults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await potentialStockApi.listResults({ page, pageSize });
      setResults(data.items);
      setTotal(data.total);
    } catch {
      setError('加载筛选结果失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  const loadTasks = useCallback(async () => {
    setTasksLoading(true);
    try {
      const data = await potentialStockApi.listTasks(10);
      setTasks(data.items);
    } catch {
      // silent
    } finally {
      setTasksLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResults();
    loadTasks();
  }, [loadResults, loadTasks]);

  const handleTriggerScan = async () => {
    setTriggering(true);
    setError(null);
    setScanSummary(null);
    setAnnouncements([]);
    setShowAnnouncements(false);
    try {
      const resp = await potentialStockApi.triggerScan({});
      setScanSummary(resp);

      // Fetch announcement details if available
      if (resp.hasDetails && resp.taskId) {
        const detail = await potentialStockApi.getTask(resp.taskId);
        if (detail.taskMeta?.announcements?.length) {
          setAnnouncements(detail.taskMeta.announcements);
        }
      }

      await loadResults();
      await loadTasks();
      // Auto-expand task history after a new scan
      setShowTaskHistory(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || '触发扫描失败');
    } finally {
      setTriggering(false);
    }
  };

  const handleStatusUpdate = async (stockCode: string, status: string) => {
    if (!status) return;
    try {
      await potentialStockApi.updateTargetStatus(stockCode, status);
      await loadResults();
    } catch {
      setError('更新状态失败');
    }
  };

  const handleViewDetail = async (item: ScreeningResultItem) => {
    setSelectedResult(item);
    setShowDetail(true);
    setDetailMd('');
    try {
      const detail = await potentialStockApi.getResultDetail(item.id);
      setDetailMd(detail.reportMd);
    } catch {
      setDetailMd('加载详情失败');
    }
  };

  const handleViewTaskDetail = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setSelectedTaskDetail(null);
    setSelectedTaskAnnouncements([]);
    try {
      const detail = await potentialStockApi.getTask(taskId);
      setSelectedTaskDetail(detail);
      setSelectedTaskAnnouncements(detail.taskMeta?.announcements || []);
    } catch {
      // silent
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const hasResults = results.length > 0;
  const hasEverScanned = tasks.length > 0;
  const showEmptyState = !loading && !hasResults && !announcements.length;

  return (
    <AppPage className="max-w-6xl space-y-6 pb-12 pt-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">潜力标的挖掘</h1>
          <p className="mt-1 text-xs text-gray-400">
            通过分析A股主板公告事件（并购重组/产能扩张/业务变更/技术合作/订单落地），
            结合基本面与产业价值评分，自动挖掘潜在投资标的。
          </p>
        </div>
        <div className="flex items-center gap-2">
          {showTaskHistory && tasks.length > 0 && (
            <span className="text-xs text-gray-400">
              共 {tasks.length} 次扫描
            </span>
          )}
          <Button onClick={handleTriggerScan} disabled={triggering}>
            {triggering ? '扫描中...' : '立即分析'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ── Scan Summary ── */}
      {scanSummary && (
        <ScanSummaryCard
          summary={scanSummary}
          announcements={announcements}
          onViewAnnouncements={() => setShowAnnouncements(true)}
        />
      )}

      {/* ── Announcements List (when user clicks to view) ── */}
      {showAnnouncements && announcements.length > 0 && (
        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-700">
              本次扫描公告明细（{announcements.length} 条）
            </h3>
            <button
              className="text-xs text-gray-400 hover:text-gray-600"
              onClick={() => setShowAnnouncements(false)}
            >
              收起
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="border-b border-gray-100 text-xs uppercase text-gray-400">
                  <th className="px-4 py-2.5 font-medium">#</th>
                  <th className="px-4 py-2.5 font-medium">标的</th>
                  <th className="px-4 py-2.5 font-medium">公告标题</th>
                  <th className="px-4 py-2.5 font-medium">日期</th>
                  <th className="px-4 py-2.5 font-medium">信号匹配</th>
                </tr>
              </thead>
              <tbody>
                {announcements.map((ann, i) => (
                  <AnnouncementRow key={ann.id} ann={ann} index={i} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── Matched Results Table ── */}
      <Card className="p-0">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            加载中...
          </div>
        ) : hasResults ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs uppercase text-gray-400">
                  <th className="px-4 py-3 font-medium">标的</th>
                  <th className="px-4 py-3 font-medium">事件类型</th>
                  <th className="px-4 py-3 font-medium">优先级</th>
                  <th className="px-4 py-3 font-medium">评分</th>
                  <th className="px-4 py-3 font-medium">评级</th>
                  <th className="px-4 py-3 font-medium">跟踪状态</th>
                  <th className="px-4 py-3 font-medium">日期</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-gray-50 transition-colors hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium">{r.stockName}</div>
                      <div className="text-xs text-gray-400">{r.stockCode}</div>
                    </td>
                    <td className="px-4 py-3">{EVENT_LABELS[r.eventType] || r.eventType}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        r.signalPriority === 'P0' ? 'bg-red-50 text-red-600' :
                        r.signalPriority === 'P1' ? 'bg-yellow-50 text-yellow-600' :
                        'bg-gray-50 text-gray-500'
                      }`}>
                        {r.signalPriority}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium">{r.compositeRating}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RATING_COLORS[r.ratingLevel] || ''}`}>
                        {r.ratingLevel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        className="rounded border border-gray-200 px-2 py-1 text-xs"
                        value={r.trackedStatus || ''}
                        onChange={(e) => handleStatusUpdate(r.stockCode, e.target.value)}
                      >
                        <option value="">-</option>
                        <option value="OBSERVING">观察中</option>
                        <option value="TRACKING">跟踪中</option>
                        <option value="REMOVED">已剔除</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {r.createdAt?.slice(0, 10)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="text-xs text-blue-500 hover:underline"
                        onClick={() => handleViewDetail(r)}
                      >
                        详情
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
                <span className="text-xs text-gray-400">共 {total} 条</span>
                <div className="flex gap-2">
                  <button
                    className="rounded px-3 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-100 disabled:opacity-30"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    上一页
                  </button>
                  <span className="px-2 py-1 text-xs text-gray-500">
                    {page} / {totalPages}
                  </span>
                  <button
                    className="rounded px-3 py-1 text-xs text-gray-500 transition-colors hover:bg-gray-100 disabled:opacity-30"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    下一页
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : !showEmptyState ? null : (
          <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-400">
            {hasEverScanned ? (
              <>
                <span>本次扫描未命中事件信号。</span>
                {announcements.length > 0 && (
                  <button
                    className="text-xs text-blue-500 hover:underline"
                    onClick={() => setShowAnnouncements(true)}
                  >
                    查看 {announcements.length} 条公告明细
                  </button>
                )}
                <span className="text-xs text-gray-400">
                  或查看下方扫描历史了解过往扫描任务明细。
                </span>
              </>
            ) : (
              <>
                <span>暂无筛选结果。</span>
                <span className="text-xs">点击「立即分析」开始扫描主板A股公告，系统将自动识别事件信号并进行评估。</span>
              </>
            )}
          </div>
        )}
      </Card>

      {/* ── 扫描历史 ── */}
      <Card>
        <button
          className="flex w-full items-center justify-between"
          onClick={() => setShowTaskHistory(!showTaskHistory)}
        >
          <h3 className="text-sm font-semibold text-gray-700">
            📋 扫描历史
            {tasks.length > 0 && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                （共 {tasks.length} 次）
              </span>
            )}
          </h3>
          <span className="text-xs text-gray-400">
            {showTaskHistory ? '收起 ▲' : '展开 ▼'}
          </span>
        </button>

        {showTaskHistory && (
          <div className="mt-3">
            {tasksLoading ? (
              <div className="py-4 text-center text-xs text-gray-400">加载中...</div>
            ) : tasks.length === 0 ? (
              <div className="py-4 text-center text-xs text-gray-400">
                暂无扫描记录。点击「立即分析」开始首次扫描。
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-gray-100 text-gray-400">
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-medium">状态</th>
                      <th className="px-3 py-2 font-medium">触发</th>
                      <th className="px-3 py-2 font-medium">时间</th>
                      <th className="px-3 py-2 font-medium">扫描范围</th>
                      <th className="px-3 py-2 font-medium">公告</th>
                      <th className="px-3 py-2 font-medium">信号</th>
                      <th className="px-3 py-2 font-medium">标的</th>
                      <th className="px-3 py-2 font-medium" />
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((t, i) => (
                      <TaskRow
                        key={t.id}
                        task={t}
                        index={i}
                        onViewDetail={handleViewTaskDetail}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* ── Result Detail Modal ── */}
      {showDetail && selectedResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="max-h-[80vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">
                {selectedResult.stockName} ({selectedResult.stockCode})
              </h2>
              <button
                className="rounded px-3 py-1 text-sm text-gray-400 hover:bg-gray-100"
                onClick={() => setShowDetail(false)}
              >
                关闭
              </button>
            </div>
            <div className="prose prose-sm max-w-none">
              {detailMd ? (
                <pre className="whitespace-pre-wrap text-sm text-gray-700">{detailMd}</pre>
              ) : (
                <p className="text-gray-400">加载中...</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Task Detail Modal ── */}
      {selectedTaskId && selectedTaskDetail && (
        <TaskDetailModal
          taskDetail={selectedTaskDetail}
          announcements={selectedTaskAnnouncements}
          onClose={() => { setSelectedTaskId(null); setSelectedTaskDetail(null); }}
        />
      )}
    </AppPage>
  );
};

export default PotentialStockMiningPage;
