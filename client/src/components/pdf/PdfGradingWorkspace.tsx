"use client";

import { Download, Loader2, MapPin, Plus, Save, Send, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { PdfAnnotation, PdfGradeRequest, PdfSubmission, RubricCriterion, RubricScore } from "@/types/grader";

const inputStyles = "h-10 w-full rounded-xl border bg-background px-3 text-sm focus:border-primary focus:outline-none";
const textareaStyles = "min-h-20 w-full rounded-xl border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none";

function initialGrade(submission: PdfSubmission): PdfGradeRequest {
  return submission.grade ?? {
    rubric: [{ id: "criterion-1", title: "Criterion 1", description: "", max_points: 10 }],
    scores: [{ criterion_id: "criterion-1", points: 0, feedback: "" }],
    annotations: [],
    overall_feedback: "",
    finalized: false
  };
}

export function PdfGradingWorkspace({
  submission,
  pending,
  onSave,
  onDownload,
  serverError
}: {
  submission: PdfSubmission;
  pending: boolean;
  onSave: (grade: PdfGradeRequest) => void;
  onDownload?: () => void;
  serverError?: string;
}) {
  const startingGrade = initialGrade(submission);
  const [rubric, setRubric] = useState<RubricCriterion[]>(startingGrade.rubric);
  const [scores, setScores] = useState<RubricScore[]>(startingGrade.scores);
  const [annotations, setAnnotations] = useState<PdfAnnotation[]>(startingGrade.annotations);
  const [overallFeedback, setOverallFeedback] = useState(startingGrade.overall_feedback);
  const [annotationPage, setAnnotationPage] = useState(1);
  const [annotationX, setAnnotationX] = useState(50);
  const [annotationY, setAnnotationY] = useState(50);
  const [annotationComment, setAnnotationComment] = useState("");
  const [error, setError] = useState<string>();
  const nextCriterion = useRef(rubric.length + 1);
  const finalized = submission.status === "finalized";
  const total = scores.reduce((sum, score) => sum + (Number.isFinite(score.points) ? score.points : 0), 0);
  const maximum = rubric.reduce((sum, criterion) => sum + (Number.isFinite(criterion.max_points) ? criterion.max_points : 0), 0);

  function updateCriterion(index: number, patch: Partial<RubricCriterion>) {
    setRubric((current) => current.map((criterion, itemIndex) => itemIndex === index ? { ...criterion, ...patch } : criterion));
  }

  function updateScore(criterionId: string, patch: Partial<RubricScore>) {
    setScores((current) => current.map((score) => score.criterion_id === criterionId ? { ...score, ...patch } : score));
  }

  function addCriterion() {
    while (rubric.some((criterion) => criterion.id === `criterion-${nextCriterion.current}`)) {
      nextCriterion.current += 1;
    }
    const number = nextCriterion.current++;
    const criterion = { id: `criterion-${number}`, title: `Criterion ${number}`, description: "", max_points: 10 };
    setRubric((current) => [...current, criterion]);
    setScores((current) => [...current, { criterion_id: criterion.id, points: 0, feedback: "" }]);
  }

  function removeCriterion(criterionId: string) {
    if (rubric.length === 1) {
      setError("A rubric needs at least one criterion.");
      return;
    }
    setRubric((current) => current.filter((criterion) => criterion.id !== criterionId));
    setScores((current) => current.filter((score) => score.criterion_id !== criterionId));
  }

  function addAnnotation() {
    if (!annotationComment.trim()) {
      setError("Enter an annotation comment.");
      return;
    }
    setAnnotations((current) => [...current, {
      page: annotationPage,
      x: annotationX / 100,
      y: annotationY / 100,
      comment: annotationComment.trim()
    }]);
    setAnnotationComment("");
    setError(undefined);
  }

  function submit(finalize: boolean) {
    const invalidCriterion = rubric.find((criterion) => !criterion.title.trim() || criterion.max_points <= 0);
    const invalidScore = scores.find((score) => {
      const criterion = rubric.find((item) => item.id === score.criterion_id);
      return !criterion || score.points < 0 || score.points > criterion.max_points;
    });
    if (invalidCriterion || invalidScore) {
      setError("Rubric titles, point values, and scores must be within their allowed ranges.");
      return;
    }
    setError(undefined);
    onSave({ rubric, scores, annotations, overall_feedback: overallFeedback.trim(), finalized: finalize });
  }

  if (finalized) {
    return (
      <Card className="p-6">
        <p className="eyebrow text-success">Finalized grade</p>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-3xl font-semibold tabular-nums">{submission.total_score} / {submission.maximum_points}</p>
            <p className="mt-1 text-sm text-muted-foreground">The rubric is locked and feedback is ready to return.</p>
          </div>
          <Button onClick={onDownload}>
            <Download aria-hidden="true" className="size-4" /> Download feedback PDF
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card className="p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="eyebrow">Rubric</p>
            <h2 className="mt-1 text-lg font-semibold">{total.toLocaleString()} / {maximum.toLocaleString()} points</h2>
          </div>
          <Button onClick={addCriterion} size="sm" variant="secondary"><Plus aria-hidden="true" className="size-4" /> Add criterion</Button>
        </div>
        <div className="mt-5 space-y-4">
          {rubric.map((criterion, index) => {
            const score = scores.find((item) => item.criterion_id === criterion.id)!;
            return (
              <fieldset className="rounded-2xl border p-4" key={criterion.id}>
                <legend className="px-2 text-sm font-medium">Criterion {index + 1}</legend>
                <div className="grid gap-3 sm:grid-cols-[1.4fr_0.6fr_auto]">
                  <label className="text-xs text-muted-foreground">Title
                    <input aria-label={`Criterion title ${index + 1}`} className={inputStyles} onChange={(event) => updateCriterion(index, { title: event.target.value })} value={criterion.title} />
                  </label>
                  <label className="text-xs text-muted-foreground">Maximum points
                    <input aria-label={`${criterion.title} maximum points`} className={inputStyles} min="0.1" onChange={(event) => updateCriterion(index, { max_points: Number(event.target.value) })} step="0.1" type="number" value={criterion.max_points} />
                  </label>
                  <Button aria-label={`Remove ${criterion.title}`} className="self-end" onClick={() => removeCriterion(criterion.id)} size="icon" variant="ghost"><Trash2 aria-hidden="true" className="size-4" /></Button>
                </div>
                <label className="mt-3 block text-xs text-muted-foreground">Description
                  <textarea aria-label={`${criterion.title} description`} className={textareaStyles} onChange={(event) => updateCriterion(index, { description: event.target.value })} value={criterion.description} />
                </label>
                <div className="mt-3 grid gap-3 sm:grid-cols-[0.45fr_1.55fr]">
                  <label className="text-xs text-muted-foreground">Score
                    <input aria-label={`${criterion.title} score`} className={inputStyles} max={criterion.max_points} min="0" onChange={(event) => updateScore(criterion.id, { points: Number(event.target.value) })} step="0.1" type="number" value={score.points} />
                  </label>
                  <label className="text-xs text-muted-foreground">Criterion feedback
                    <textarea aria-label={`${criterion.title} feedback`} className={textareaStyles} onChange={(event) => updateScore(criterion.id, { feedback: event.target.value })} value={score.feedback} />
                  </label>
                </div>
              </fieldset>
            );
          })}
        </div>
      </Card>

      <Card className="p-5 sm:p-6">
        <div className="flex items-center gap-3"><MapPin aria-hidden="true" className="size-5 text-primary" /><h2 className="font-semibold">Page annotations</h2></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="text-xs text-muted-foreground">Page
            <select aria-label="Annotation page" className={inputStyles} onChange={(event) => setAnnotationPage(Number(event.target.value))} value={annotationPage}>
              {Array.from({ length: submission.page_count }, (_, index) => <option key={index + 1} value={index + 1}>Page {index + 1}</option>)}
            </select>
          </label>
          <label className="text-xs text-muted-foreground">Horizontal position (%)
            <input aria-label="Horizontal position percent" className={inputStyles} max="100" min="0" onChange={(event) => setAnnotationX(Number(event.target.value))} type="number" value={annotationX} />
          </label>
          <label className="text-xs text-muted-foreground">Vertical position (%)
            <input aria-label="Vertical position percent" className={inputStyles} max="100" min="0" onChange={(event) => setAnnotationY(Number(event.target.value))} type="number" value={annotationY} />
          </label>
        </div>
        <label className="mt-3 block text-xs text-muted-foreground">Comment
          <textarea aria-label="Annotation comment" className={textareaStyles} onChange={(event) => setAnnotationComment(event.target.value)} value={annotationComment} />
        </label>
        <Button className="mt-3" onClick={addAnnotation} size="sm" variant="secondary"><Plus aria-hidden="true" className="size-4" /> Add annotation</Button>
        {annotations.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {annotations.map((annotation, index) => (
              <li className="flex items-start justify-between gap-3 rounded-xl bg-muted/50 p-3 text-sm" key={annotation.id ?? `${annotation.page}-${index}`}>
                <span><strong>Page {annotation.page}</strong> · {Math.round(annotation.x * 100)}%, {Math.round(annotation.y * 100)}% — {annotation.comment}</span>
                <Button aria-label={`Remove annotation ${index + 1}`} onClick={() => setAnnotations((current) => current.filter((_, itemIndex) => itemIndex !== index))} size="icon" variant="ghost"><Trash2 aria-hidden="true" className="size-4" /></Button>
              </li>
            ))}
          </ul>
        ) : null}
      </Card>

      <Card className="p-5 sm:p-6">
        <label className="block text-sm font-medium">Overall feedback
          <textarea aria-label="Overall feedback" className={`${textareaStyles} mt-2 min-h-28`} onChange={(event) => setOverallFeedback(event.target.value)} value={overallFeedback} />
        </label>
        {error || serverError ? <p className="mt-3 text-sm text-danger" role="alert">{error ?? serverError}</p> : null}
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <Button disabled={pending} onClick={() => submit(false)} variant="secondary">{pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <Save aria-hidden="true" className="size-4" />} Save draft</Button>
          <Button disabled={pending} onClick={() => submit(true)}><Send aria-hidden="true" className="size-4" /> Finalize grade</Button>
        </div>
      </Card>
    </div>
  );
}
