import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://yguzfqsgkttohbxqwmnp.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlndXpmcXNna3R0b2hieHF3bW5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEwMTA0NzcsImV4cCI6MjEwNjU4NjQ3N30.ajMjfIQZ4lShjI1LPtwJ9gOpoKypxuomQSUDJNa_lh4'

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
