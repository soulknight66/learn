# Exercise: review a VM arithmetic dispatch

Review review.c under the public integer and resource requirements. Find every path that can invoke
undefined behavior, read outside the stack, or violate the exact step budget. Rank findings by impact
and propose checks that occur before state is irreversibly mutated.
