import { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ErrorBoundary } from '@/components/error-boundary';
import { AppShell } from '@/components/app-shell';
import Home from '@/pages/home';
import Analyze from '@/pages/analyze';
import History from '@/pages/history';
import PetProfile from '@/pages/pet';
import NotFound from '@/pages/not-found';
import { useLocalData } from '@/hooks/use-local-data';
import { Route, Router as WouterRouter, Switch, useLocation } from 'wouter';

const queryClient = new QueryClient();

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function Router() {
  const data = useLocalData();
  return (
    <AppShell>
      <RoutedErrorBoundary>
        <Switch>
          <Route path="/" component={() => <Home pets={data.pets} analyses={data.analyses} />} />
          <Route path="/analyze" component={() => <Analyze pets={data.pets} addAnalysis={data.addAnalysis} />} />
          <Route path="/history" component={() => <History pets={data.pets} analyses={data.analyses} deleteAnalysis={data.deleteAnalysis} />} />
          <Route path="/history/:id" component={() => <History pets={data.pets} analyses={data.analyses} deleteAnalysis={data.deleteAnalysis} />} />
          <Route path="/pet" component={() => <PetProfile pets={data.pets} addPet={data.addPet} updatePet={data.updatePet} />} />
          <Route component={NotFound} />
        </Switch>
      </RoutedErrorBoundary>
    </AppShell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;