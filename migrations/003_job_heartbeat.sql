-- 003_job_heartbeat.sql
--
-- Liveness signal for background evaluation jobs.
--
-- `status` records what was asked for, not whether the process doing it is
-- alive. `_execute_evaluation` runs in-process, so a worker restart — a deploy,
-- an OOM, a free-tier service idling out — leaves the row `running` forever and
-- the dashboard shows a job that will never finish.
--
-- The job touches `heartbeat_at` as each prompt completes. A row that has gone
-- quiet for longer than any prompt could reasonably take is swept to `failed`
-- (see aeo_engine/jobs.py). Nullable on purpose: rows written before this
-- column existed have no heartbeat, and the sweep falls back to `created_at`
-- for them rather than treating NULL as dead.

ALTER TABLE evaluations
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

-- The sweep reads only in-flight rows, which are a tiny minority of the table.
CREATE INDEX IF NOT EXISTS idx_evaluations_running_heartbeat
    ON evaluations (heartbeat_at)
    WHERE status = 'running';
