-- Supabase Realtime authorization for class chat (run once per project, as the project owner).
--
-- Class chat uses PRIVATE broadcast + presence channels named  class-chat:<classroom uuid>.
-- Only ping events ("something changed") and presence/typing travel over Realtime: never message text, files or names of
-- anyone's account. Real content always comes from the API, which checks class membership on every request.
--
-- Realtime reads these policies on realtime.messages (a managed table; we only ADD two policies, nothing is altered).
-- The helper is SECURITY DEFINER so the policy can look at class membership although browsers have no table access.

create or replace function zenith.can_join_class_chat(topic text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  with t as (select split_part(topic, ':', 1) as kind, split_part(topic, ':', 2) as cid)
  select exists (
    select 1 from t
    where t.kind = 'class-chat'
      and t.cid ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
      and (
        exists (select 1 from zenith.class_members m where m.classroom_id = t.cid::uuid and m.student_id = (select auth.uid()) and m.status = 'active')
        or exists (select 1 from zenith.classrooms c where c.id = t.cid::uuid and c.teacher_id = (select auth.uid()))
      )
  );
$$;

revoke all on function zenith.can_join_class_chat(text) from public, anon;
grant execute on function zenith.can_join_class_chat(text) to authenticated;

drop policy if exists "zenith class chat receive" on realtime.messages;
create policy "zenith class chat receive" on realtime.messages
  for select to authenticated
  using ( realtime.messages.extension in ('broadcast', 'presence') and zenith.can_join_class_chat((select realtime.topic())) );

drop policy if exists "zenith class chat send" on realtime.messages;
create policy "zenith class chat send" on realtime.messages
  for insert to authenticated
  with check ( realtime.messages.extension in ('broadcast', 'presence') and zenith.can_join_class_chat((select realtime.topic())) );
