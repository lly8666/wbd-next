use std::sync::atomic::{AtomicUsize, Ordering};

pub(crate) fn add_within(counter: &AtomicUsize, by: usize, max: usize) -> bool {
    let mut cur = counter.load(Ordering::Acquire);
    loop {
        let Some(next) = cur.checked_add(by).filter(|&n| n <= max) else {
            return false;
        };
        match counter.compare_exchange_weak(cur, next, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) => return true,
            Err(actual) => cur = actual,
        }
    }
}

