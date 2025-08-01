from database import SessionLocal, eval_job_table, eval_metrics_table, gold_qa_batch_table, gold_qa_table
from sqlalchemy import select, insert, func
from sqlalchemy.orm import Session
import uuid

def create_eval_job(qa_batch_id: str, repo_id: str):
    """Create a new evaluation job"""
    with SessionLocal() as session:
        # Verify the QA batch exists and belongs to the repo
        stmt = select(gold_qa_batch_table).where(
            gold_qa_batch_table.c.id == uuid.UUID(qa_batch_id),
            gold_qa_batch_table.c.repo_id == uuid.UUID(repo_id)
        )
        batch = session.execute(stmt).fetchone()
        if not batch:
            raise ValueError(f"QA batch {qa_batch_id} not found for repo {repo_id}")
        
        # Count total QA pairs for this batch
        stmt = select(func.count()).select_from(gold_qa_table).where(
            gold_qa_table.c.batch_id == uuid.UUID(qa_batch_id),
            gold_qa_table.c.archived == False
        )
        total_qa_pairs = session.execute(stmt).scalar_one()
        
        # Create eval job
        stmt = insert(eval_job_table).values(
            qa_batch_id=uuid.UUID(qa_batch_id),
            repo_id=uuid.UUID(repo_id),
            total_qa_pairs=total_qa_pairs
        ).returning(eval_job_table.c.id)
        
        result = session.execute(stmt)
        eval_job_id = result.scalar_one()
        session.commit()
        
        job_creation_info = {
            "job_id": f"eval-job-{eval_job_id}",
            "job_type": "eval"
        }
        
        return str(eval_job_id), job_creation_info

def get_eval_jobs(repo_id: str, page: int = 1, page_size: int = 20):
    """Get paginated list of eval jobs for a repository"""
    with SessionLocal() as session:
        # Count total eval jobs
        stmt = select(func.count()).select_from(eval_job_table).where(
            eval_job_table.c.repo_id == uuid.UUID(repo_id)
        )
        total_jobs = session.execute(stmt).scalar_one()
        
        # Get paginated eval jobs with batch info
        offset = (page - 1) * page_size
        stmt = select(
            eval_job_table,
            gold_qa_batch_table.c.added_at.label('batch_created_at')
        ).select_from(
            eval_job_table.join(
                gold_qa_batch_table,
                eval_job_table.c.qa_batch_id == gold_qa_batch_table.c.id
            )
        ).where(
            eval_job_table.c.repo_id == uuid.UUID(repo_id)
        ).order_by(
            eval_job_table.c.created_at.desc()
        ).offset(offset).limit(page_size)
        
        results = session.execute(stmt).fetchall()
        
        eval_jobs = []
        for row in results:
            eval_jobs.append({
                "id": str(row.id),
                "qa_batch_id": str(row.qa_batch_id),
                "status": row.status,
                "total_qa_pairs": row.total_qa_pairs,
                "processed_qa_pairs": row.processed_qa_pairs,
                "created_at": row.created_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "batch_created_at": row.batch_created_at.isoformat()
            })
        
        return eval_jobs, total_jobs, page, page_size

def get_eval_metrics(eval_job_id: str, page: int = 1, page_size: int = 50):
    """Get paginated list of evaluation metrics for an eval job"""
    with SessionLocal() as session:
        # Count total metrics
        stmt = select(func.count()).select_from(eval_metrics_table).where(
            eval_metrics_table.c.eval_job_id == uuid.UUID(eval_job_id)
        )
        total_metrics = session.execute(stmt).scalar_one()
        
        # Get paginated metrics with QA info
        offset = (page - 1) * page_size
        stmt = select(
            eval_metrics_table,
            gold_qa_table.c.question,
            gold_qa_table.c.answer.label('expected_answer'),
            gold_qa_table.c.file_id
        ).select_from(
            eval_metrics_table.join(
                gold_qa_table,
                eval_metrics_table.c.qa_id == gold_qa_table.c.id
            )
        ).where(
            eval_metrics_table.c.eval_job_id == uuid.UUID(eval_job_id)
        ).order_by(
            eval_metrics_table.c.created_at.desc()
        ).offset(offset).limit(page_size)
        
        results = session.execute(stmt).fetchall()
        
        metrics = []
        for row in results:
            metrics.append({
                "id": str(row.id),
                "qa_id": str(row.qa_id),
                "question": row.question,
                "expected_answer": row.expected_answer,
                "actual_answer": row.actual_answer,
                "relevant_chunks": row.relevant_chunks,
                "metrics": row.metrics,
                "file_id": str(row.file_id),
                "created_at": row.created_at.isoformat()
            })
        
        return metrics, total_metrics, page, page_size

def get_eval_overall_metrics(eval_job_id: str):
    """Get overall metrics summary for an eval job"""
    with SessionLocal() as session:
        # Get all metrics for this eval job
        stmt = select(eval_metrics_table.c.metrics).where(
            eval_metrics_table.c.eval_job_id == uuid.UUID(eval_job_id),
            eval_metrics_table.c.metrics["status"].astext == "completed"
        )
        results = session.execute(stmt).fetchall()
        
        if not results:
            return {
                "total_evaluated": 0,
                "metrics_summary": {}
            }
        
        # Initialize metric aggregators
        metric_scores = {
            "g_eval_correctness": [],
            "g_eval_coherence": [],
            "g_eval_tonality": [],
            "g_eval_safety": [],
            "dag_score": [],
            "contextual_relevancy": [],
            "contextual_precision": [],
            "contextual_recall": [],
            "answer_relevancy": [],
            "answer_faithfulness": []
        }
        
        metric_pass_counts = {key: 0 for key in metric_scores.keys()}
        
        # Aggregate metrics
        for row in results:
            metrics = row.metrics
            for metric_name in metric_scores.keys():
                if metric_name in metrics:
                    score = metrics[metric_name].get("score", 0)
                    passed = metrics[metric_name].get("passed", False)
                    
                    metric_scores[metric_name].append(score)
                    if passed:
                        metric_pass_counts[metric_name] += 1
        
        # Calculate summaries
        total_evaluated = len(results)
        metrics_summary = {}
        
        for metric_name, scores in metric_scores.items():
            if scores:
                metrics_summary[metric_name] = {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "pass_rate": metric_pass_counts[metric_name] / len(scores),
                    "total_passed": metric_pass_counts[metric_name],
                    "total_evaluated": len(scores)
                }
        
        return {
            "total_evaluated": total_evaluated,
            "metrics_summary": metrics_summary
        }