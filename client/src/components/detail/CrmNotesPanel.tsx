"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { format, parseISO } from "date-fns";

interface CrmNote {
    note_type?: string;
    channel?: string;
    resolved?: boolean;
    sentiment_score?: number;
    note_text?: string;
    created_at?: string;
}

interface CrmSummary {
    total_complaints?: number;
    unresolved_count?: number;
}

type CrmNotesPanelProps = {
    notes: CrmNote[] | CrmSummary | null;
};

export function CrmNotesPanel({ notes }: CrmNotesPanelProps) {
    if (!notes) {
        return (
            <Card className="shadow-sm border-gray-200">
                <CardContent className="flex items-center justify-center h-40 text-slate-400 text-sm">
                    No CRM notes available
                </CardContent>
            </Card>
        );
    }

    if (Array.isArray(notes)) {
        if (notes.length === 0) {
            return (
                <Card className="shadow-sm border-gray-200">
                    <CardContent className="flex items-center justify-center h-40 text-slate-400 text-sm">
                        No CRM notes available
                    </CardContent>
                </Card>
            );
        }

        const getNoteColor = (type?: string) => {
            switch (type) {
                case 'complaint': return 'bg-red-100 text-red-700 hover:bg-red-200';
                case 'enquiry': return 'bg-blue-100 text-blue-700 hover:bg-blue-200';
                case 'feedback': return 'bg-green-100 text-green-700 hover:bg-green-200';
                case 'visit_note': return 'bg-slate-100 text-slate-700 hover:bg-slate-200';
                default: return 'bg-slate-100 text-slate-700';
            }
        };

        const getSentimentDot = (score: number) => {
            if (score > 0.2) return 'bg-green-500';
            if (score < -0.2) return 'bg-red-500';
            return 'bg-slate-400';
        };

        return (
            <Card className="shadow-sm border-gray-200">
                <CardHeader>
                    <CardTitle className="text-base font-semibold text-slate-900 flex items-center justify-between">
                        Interaction Timeline
                        <span className="text-sm font-normal text-slate-500">{notes.length} notes</span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="relative border-l border-slate-200 ml-3 pl-6 space-y-8 py-2">
                        {notes.map((note, idx) => {
                            const dateStr = note.created_at;
                            let displayDate = dateStr || '';
                            if (dateStr) {
                                try {
                                    displayDate = format(parseISO(dateStr), 'MMM d, yyyy h:mm a');
                                } catch { }
                            }

                            return (
                                <div key={idx} className="relative">
                                    <div className="absolute -left-[31px] top-1 h-4 w-4 rounded-full border-2 border-white bg-slate-300 ring-1 ring-slate-200" />

                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-medium text-slate-500 w-36 shrink-0">{displayDate}</span>
                                            <Badge variant="secondary" className={`font-medium border-none py-0 uppercase text-[10px] tracking-wider ${getNoteColor(note.note_type)}`}>
                                                {note.note_type?.replace('_', ' ')}
                                            </Badge>
                                            <Badge variant="outline" className="font-medium bg-slate-50 uppercase text-[10px] text-slate-500">
                                                {note.channel}
                                            </Badge>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            {note.resolved !== undefined && (
                                                <span className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded ${note.resolved ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                                                    {note.resolved ? 'Resolved' : 'Open'}
                                                </span>
                                            )}
                                            <div className="flex items-center gap-1.5" title={`Sentiment: ${note.sentiment_score}`}>
                                                <div className={`w-2 h-2 rounded-full ${getSentimentDot(Number(note.sentiment_score))}`} />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-slate-50 rounded-md p-4 mt-2 text-sm text-slate-700 leading-relaxed border border-slate-100">
                                        {note.note_text}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="shadow-sm border-gray-200">
            <CardHeader>
                <CardTitle className="text-base font-semibold text-slate-900">CRM Summary</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="text-2xl font-bold text-slate-900">{notes.total_complaints ?? 0}</div>
                        <div className="text-sm text-slate-500">Total Complaints</div>
                    </div>
                    <div className="p-4 bg-red-50 rounded-lg">
                        <div className="text-2xl font-bold text-red-600">{notes.unresolved_count ?? 0}</div>
                        <div className="text-sm text-red-500">Unresolved</div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
