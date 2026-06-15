import { useState } from 'react';
import { AnalysisResult } from '@/types';

export function useOutreachStream() {
    const [content, setContent] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    const startStream = async (customerId: string, channel: string, analysisResult: AnalysisResult) => {
        setContent('');
        setIsStreaming(true);
        setIsComplete(false);
        setError(null);

        try {
            const token = typeof window !== 'undefined' ? localStorage.getItem('pcop_token') : null;
            const response = await fetch(`/api/outreach/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    customer_id: customerId,
                    channel: channel.toLowerCase(),
                    analysis_result: analysisResult
                }),
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error('No readable stream available');

            const decoder = new TextDecoder();
            let streamBuffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                streamBuffer += decoder.decode(value, { stream: true });

                const lines = streamBuffer.split('\n\n');
                streamBuffer = lines.pop() || ''; // Keep partial line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.type === 'token') {
                                setContent(prev => prev + data.content);
                            } else if (data.type === 'done') {
                                setIsComplete(true);
                                setIsStreaming(false);
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE:', e, line);
                        }
                    }
                }
            }

            // Attempt to decode any remainder
            if (streamBuffer.length > 0) {
                const line = streamBuffer;
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'token') {
                            setContent(prev => prev + data.content);
                        }
                    } catch (e) { }
                }
            }

        } catch (err) {
            console.error('Stream error:', err);
            setError(err instanceof Error ? err : new Error('Failed to stream outreach'));
            setIsStreaming(false);
            setIsComplete(true); // Stop loading state
        }
    };

    const reset = () => {
        setContent('');
        setIsStreaming(false);
        setIsComplete(false);
        setError(null);
    };

    return { content, isStreaming, isComplete, error, startStream, reset };
}
