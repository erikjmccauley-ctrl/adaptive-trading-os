from dataclasses import dataclass, field


@dataclass
class Rule:
    id:          str
    name:        str
    status:      str      # 'active' | 'candidate' | 'retired'
    action:      str      # 'block' | 'score_adjust'
    condition:   str      # signal field: 'near_level' | 'entry_tf' | 'signal_type' |
                          #   'quality' | 'regime' | 'rr' | 'direction'
    operator:    str      # 'eq' | 'neq' | 'in' | 'not_in' | 'lt' | 'gt'
    value:       object   # e.g. 'D_FR1' | ['D_FR1', 'D_S2'] | 2.0
    score_delta: float = 0.0
    source:      str   = 'manual'   # 'inference' | 'manual' | 'backtest'
    min_trades:  int   = 0
    note:        str   = ''
    created:     str   = ''
