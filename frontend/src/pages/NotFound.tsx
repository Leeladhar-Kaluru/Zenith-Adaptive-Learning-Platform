import { EmptyState, Button } from '../ui/kit';

export default function NotFound() {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20 }}>
      <EmptyState icon="compass" title="This path leads nowhere" text="The page you are looking for does not exist or has moved. Let us get you back on the trail." action={<Button to="/" variant="brand" iconRight="arrowR">Take me home</Button>} />
    </div>
  );
}
