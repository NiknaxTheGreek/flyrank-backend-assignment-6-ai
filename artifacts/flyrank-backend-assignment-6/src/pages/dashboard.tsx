import { useState } from 'react';
import {
  getHealthCheckQueryKey,
  useClassifySupportMessage,
  useHealthCheck,
} from '@workspace/api-client-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';

export default function Dashboard() {
  const [text, setText] = useState('');
  
  // Refetch every 10 seconds to keep UI fresh
  const health = useHealthCheck({
    query: { queryKey: getHealthCheckQueryKey(), refetchInterval: 10000 },
  });
  const classify = useClassifySupportMessage();
  
  const isHealthy = health.isSuccess;
  
  const handleSubmit = () => {
    if (!text.trim()) return;
    classify.mutate({ data: { text } });
  };
  
  const handleReset = () => {
    setText('');
    classify.reset();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col p-4 md:p-8">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold uppercase tracking-tight">FlyRank Classifier Console</h1>
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider mt-1">
            Experiment Lab Notebook &middot; API v0.1.0
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Card className="px-4 py-2 flex items-center gap-3 bg-white/50 backdrop-blur-sm rounded-[2px] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border-2">
            <span className="text-sm font-mono font-bold uppercase">System Status</span>
            <div className="flex items-center gap-1.5">
              {health.isLoading ? (
                <Skeleton className="w-3 h-3 rounded-full" />
              ) : (
                <div className={`w-3 h-3 rounded-full border border-foreground shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] ${isHealthy ? 'bg-green-400' : 'bg-red-500'}`} />
              )}
              <span className="text-xs font-mono font-bold uppercase">{isHealthy ? 'Online' : 'Offline'}</span>
            </div>
          </Card>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* LEFT PANEL: INPUT */}
        <section className="flex flex-col gap-4">
          <Card className="flex flex-col h-full bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <div className="flex justify-between items-center">
                <CardTitle>Input Context</CardTitle>
                <Badge variant="outline" className="bg-background">POST /api/llm/classify</Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col gap-4">
              <div className="flex-1 flex flex-col gap-2">
                <Label htmlFor="support-text">Customer Support Message</Label>
                <Textarea 
                  id="support-text"
                  placeholder="Paste customer support inquiry here... (e.g. 'I was charged twice for my subscription this month.')"
                  className="flex-1 resize-none min-h-[300px] text-base"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={onKeyDown}
                  disabled={classify.isPending}
                />
                <p className="text-xs text-muted-foreground font-mono text-right uppercase mt-1">Cmd/Ctrl + Enter to submit</p>
              </div>

              <div className="flex gap-4 pt-4 border-t-2 border-foreground/10 border-dashed">
                <Button 
                  onClick={handleSubmit} 
                  disabled={classify.isPending || !text.trim()} 
                  className="flex-1"
                  size="lg"
                >
                  {classify.isPending ? 'Processing...' : 'Run Classification'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleReset}
                  disabled={classify.isPending || (!text && !classify.data && !classify.isError)}
                  size="lg"
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* RIGHT PANEL: RESULT */}
        <section className="flex flex-col gap-4 h-full">
          <Card className="flex flex-col h-full bg-secondary/5 border-secondary overflow-hidden">
            <CardHeader className="bg-secondary/10 border-b-2 border-secondary pb-4">
              <CardTitle className="text-secondary-foreground">Evaluation Record</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 flex flex-col">
              {!classify.data && !classify.isPending && !classify.isError && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-12 opacity-50">
                  <div className="w-16 h-16 border-2 border-dashed border-foreground rounded-[2px] flex items-center justify-center mb-4">
                    <span className="font-mono text-2xl">?</span>
                  </div>
                  <p className="font-mono text-sm uppercase tracking-wider">Awaiting Input</p>
                  <p className="text-xs text-muted-foreground mt-2 max-w-xs">
                    Run the classification to inspect structured categorization, urgency, and operational metadata.
                  </p>
                </div>
              )}

              {classify.isPending && (
                <div className="flex-1 p-6 flex flex-col gap-6 animate-pulse">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Skeleton className="h-4 w-20" /><Skeleton className="h-8 w-32" /></div>
                    <div className="space-y-2"><Skeleton className="h-4 w-20" /><Skeleton className="h-8 w-24" /></div>
                  </div>
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-24 w-full" />
                  </div>
                  <div className="mt-auto grid grid-cols-3 gap-4 pt-4 border-t-2 border-foreground/10 border-dashed">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                </div>
              )}

              {classify.isError && (
                <div className="flex-1 p-6 flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 bg-destructive text-destructive-foreground border-2 border-foreground rounded-[2px] flex items-center justify-center mb-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    <span className="font-mono text-2xl font-bold">!</span>
                  </div>
                  <h3 className="font-bold text-lg uppercase tracking-tight mb-2">Operation Failed</h3>
                  <p className="text-sm font-mono text-muted-foreground max-w-md">
                    The classification endpoint returned an error. Ensure the backend is running and reachable.
                  </p>
                </div>
              )}

              {classify.isSuccess && classify.data && (
                <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="p-6 grid grid-cols-2 md:grid-cols-3 gap-6">
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-muted-foreground">Category</Label>
                      <Badge variant="outline" className="w-fit text-sm py-1 bg-white">
                        {classify.data.category}
                      </Badge>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-muted-foreground">Urgency</Label>
                      <Badge 
                        variant={classify.data.urgency === 'high' ? 'destructive' : (classify.data.urgency === 'normal' ? 'warning' : 'success')} 
                        className="w-fit text-sm py-1"
                      >
                        {classify.data.urgency}
                      </Badge>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-muted-foreground">Confidence</Label>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xl font-bold">
                          {(classify.data.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="px-6 py-4 bg-white border-y-2 border-foreground/10">
                    <Label className="text-muted-foreground mb-2 block">Verification Notes (Reasoning)</Label>
                    <p className="font-serif text-lg leading-relaxed text-foreground/90">
                      {classify.data.reason}
                    </p>
                  </div>

                  <div className="p-6 bg-secondary/5 mt-auto">
                    <Label className="text-muted-foreground mb-4 block">Operational Metadata</Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm font-mono">
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Provider</span>
                        <span className="font-bold truncate" title={classify.data.metadata.provider}>{classify.data.metadata.provider}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Model</span>
                        <span className="font-bold truncate" title={classify.data.metadata.model}>{classify.data.metadata.model}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Duration</span>
                        <span className="font-bold">{classify.data.metadata.duration_ms}ms</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Cache</span>
                        <span className="font-bold">{classify.data.metadata.cache_hit ? 'HIT' : 'MISS'}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Tokens (In/Out)</span>
                        <span className="font-bold">
                          {classify.data.metadata.input_tokens ?? '-'} / {classify.data.metadata.output_tokens ?? '-'}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase">Retries</span>
                        <span className="font-bold">{classify.data.metadata.retries}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </section>

      </main>
    </div>
  );
}