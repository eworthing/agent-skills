# Changes

`effective_value` and `describe_source` now share one resolution step.
`_resolve` walks the layers once and returns both the value and the name of
the layer it came from; each public function projects one half of that pair.

Before this change the two functions each walked the layer order on their
own. They are answers to the same question -- which layer owns this key --
and keeping two walks meant they could disagree, which they did.

No change to the layer order or to which value any key resolves to.
