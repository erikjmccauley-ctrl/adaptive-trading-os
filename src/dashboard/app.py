"""
MES Signal Bot — Dashboard
Run: streamlit run src/dashboard/app.py
"""
import pandas as pd
import streamlit as st

from src.dashboard.data import (
    load_todays_signals,
    load_outcomes,
    load_bucket_analysis,
    total_backtest_trades,
    load_risk_state,
    load_rules,
    promote_rule,
    retire_rule,
)
from src.risk.limits import MAX_TRADES_PER_DAY

st.set_page_config(page_title='MES Signal Bot', page_icon='📈', layout='wide')
st.title('MES Signal Bot')

tab_today, tab_rules, tab_perf, tab_history = st.tabs(
    ['Today', 'Rules', 'Performance', 'History']
)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Today
# ══════════════════════════════════════════════════════════════════════════════

with tab_today:
    state = load_risk_state()

    # Kill switch banner
    if state.kill_switch_active:
        st.error(f'⛔ KILL SWITCH ACTIVE — {state.kill_switch_reason}')

    # Risk state metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Trades today', f'{state.trades_taken} / {MAX_TRADES_PER_DAY}')
    pnl_sign = '+' if state.daily_pnl >= 0 else ''
    col2.metric('Daily P&L', f'{pnl_sign}${state.daily_pnl:.2f}')
    col3.metric('Consecutive losses', state.consecutive_losses)
    trades_left = max(0, MAX_TRADES_PER_DAY - state.trades_taken)
    col4.metric('Trades remaining', trades_left)

    st.divider()

    # Today's signals
    st.subheader("Today's signals")
    signals = load_todays_signals()
    if signals:
        sig_df = pd.DataFrame(signals)
        show_cols = [c for c in
                     ['time', 'direction', 'entry_tf', 'near_level', 'quality', 'rr', 'entry', 'stop', 'target1']
                     if c in sig_df.columns]
        st.dataframe(sig_df[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info('No signals fired today.')

    st.divider()

    # Today's outcomes
    st.subheader("Today's outcomes")
    all_outcomes = load_outcomes(days=1)
    if not all_outcomes.empty and 'date' in all_outcomes.columns:
        today_str = pd.Timestamp.now().normalize()
        today_out = all_outcomes[all_outcomes['date'] >= today_str]
    else:
        today_out = all_outcomes

    if not today_out.empty:
        wins     = (today_out['outcome'] == 'WIN').sum()
        losses   = (today_out['outcome'] == 'LOSS').sum()
        timeouts = (today_out['outcome'] == 'TIMEOUT').sum()
        total_pnl = today_out['pnl_dollars'].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Total P&L', f'{"+" if total_pnl >= 0 else ""}${total_pnl:.2f}')
        m2.metric('Wins', int(wins))
        m3.metric('Losses', int(losses))
        m4.metric('Timeouts', int(timeouts))

        show_cols = [c for c in
                     ['exit_time', 'outcome', 'pnl_dollars', 'r_multiple', 'exit_price', 'signal_id']
                     if c in today_out.columns]
        st.dataframe(today_out[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info('No paper trades resolved today.')


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Rules
# ══════════════════════════════════════════════════════════════════════════════

with tab_rules:
    active_rules, candidate_rules = load_rules()

    st.subheader(f'Active rules ({len(active_rules)})')
    if active_rules:
        for rule in active_rules:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{rule.name}** `{rule.id}`  \n"
                            f"`{rule.condition} {rule.operator} {rule.value}`  \n"
                            f"_{rule.note}_")
                if c2.button('Retire', key=f'retire_active_{rule.id}'):
                    retire_rule(rule.id)
                    st.rerun()
    else:
        st.info('No active rules.')

    st.divider()

    st.subheader(f'Candidate rules ({len(candidate_rules)})')
    if candidate_rules:
        for rule in candidate_rules:
            with st.container(border=True):
                c1, c2, c3 = st.columns([5, 1, 1])
                c1.markdown(f"**{rule.name}** `{rule.id}`  \n"
                            f"`{rule.condition} {rule.operator} {rule.value}`  \n"
                            f"_{rule.note}_")
                if c2.button('Promote', key=f'promote_{rule.id}'):
                    promote_rule(rule.id)
                    st.rerun()
                if c3.button('Retire', key=f'retire_cand_{rule.id}'):
                    retire_rule(rule.id)
                    st.rerun()
    else:
        st.info('No candidate rules.')


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Performance
# ══════════════════════════════════════════════════════════════════════════════

with tab_perf:
    n_total = total_backtest_trades()
    if n_total:
        st.caption(f'Based on {n_total} backtest trades across all CSVs.')
    else:
        st.warning('No backtest CSV files found. Run backtest.py first.')

    dimension = st.selectbox(
        'Group by',
        ['signal_type', 'quality', 'regime', 'entry_tf', 'near_level', 'direction'],
        index=0,
    )

    df_perf = load_bucket_analysis(dimension)
    if df_perf is not None and not df_perf.empty:
        conf_colors = {
            'A':                 '🟢',
            'B':                 '🟡',
            'C':                 '🟠',
            'insufficient-data': '⚫',
        }
        df_perf['grade'] = df_perf['confidence'].map(lambda c: conf_colors.get(c, '') + ' ' + c)
        show_cols = [dimension, 'n', 'win_rate', 'profit_factor', 'expectancy_r', 'net_pnl', 'grade']
        show_cols = [c for c in show_cols if c in df_perf.columns]
        st.dataframe(
            df_perf[show_cols].rename(columns={
                'win_rate':     'WR %',
                'profit_factor': 'PF',
                'expectancy_r': 'Exp (R)',
                'net_pnl':      'Net P&L ($)',
                'grade':        'Confidence',
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info('No data for this dimension yet.')


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — History
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    df_hist = load_outcomes(days=30)

    if df_hist.empty:
        st.info('No paper trade history yet. Start paper trading to populate this panel.')
    else:
        # Daily summary table
        if 'date' in df_hist.columns:
            daily = (
                df_hist.groupby(df_hist['date'].dt.date)
                .agg(
                    trades=('outcome', 'count'),
                    wins=('outcome', lambda x: (x == 'WIN').sum()),
                    losses=('outcome', lambda x: (x == 'LOSS').sum()),
                    net_pnl=('pnl_dollars', 'sum'),
                )
                .reset_index()
                .rename(columns={'date': 'Date'})
                .sort_values('Date', ascending=False)
            )
            daily['net_pnl'] = daily['net_pnl'].round(2)

            st.subheader('Daily summary (last 30 days)')
            st.dataframe(daily, use_container_width=True, hide_index=True)

            # Cumulative P&L chart
            st.subheader('Cumulative P&L')
            df_sorted  = df_hist.sort_values('date')
            cum_pnl    = df_sorted['pnl_dollars'].cumsum().reset_index(drop=True)
            chart_data = pd.DataFrame({'Cumulative P&L ($)': cum_pnl})
            st.line_chart(chart_data)

        else:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
