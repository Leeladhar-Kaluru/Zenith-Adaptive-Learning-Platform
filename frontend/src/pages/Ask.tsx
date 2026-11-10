import AskPanel from '../ask/AskPanel';
import { Card } from '../ui/kit';
import s from './pages.module.css';

export default function Ask() {
  return (
    <div className={s.stack} style={{ maxWidth: 820, margin: '0 auto' }}>
      <div><h1 className={s.title}>Ask ZENITH</h1><p className={s.lead}>Your study helper. It asks you questions to help you find the answer yourself.</p></div>
      <Card><AskPanel /></Card>
    </div>
  );
}
