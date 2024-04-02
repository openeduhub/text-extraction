from abc import abstractmethod
from typing import Callable, Optional, Protocol, Type
from urllib.parse import urlparse

from pyrate_limiter import (
    AbstractBucket,
    AbstractClock,
    BucketFactory,
    Duration,
    InMemoryBucket,
    Limiter,
    Rate,
    RateItem,
    TimeClock,
)

#: A rate strategy assigns rates (e.g. 1000 / s) to (domain) names. While this
#: can be a simple mapping, using a function allows for a bit more flexibility.
#: Note that this function is called only once, at the creation of a new
#: ``Bucket`` (i.e. when a domain is seen for the first time). Thus, there can
#: be no dynamism in how the ``Rate``s are chosen -- only the
#: ``WeightStrategy`` can support this.
RateStrategy = Callable[[str], list[Rate]]


def get_simple_rate_strategy(max_rate_per_second: int = 100) -> RateStrategy:
    """
    A very simple ``RateStrategy`` that simply assigns a fixed rate limit
    per second and 10 times that limit per minute to any domain name.
    """
    return lambda _: [
        Rate(limit=max_rate_per_second, interval=Duration.SECOND),
        Rate(limit=10 * max_rate_per_second, interval=Duration.MINUTE),
    ]


class WeightStrategy(Protocol):
    @abstractmethod
    def __call__(self, name: str, weight: int, bucket: Optional[AbstractBucket]) -> int:
        """
        Assign a weight (i.e. a measure of "cost") to a (domain) name.

        If the total weight within a time-frame is larger than any rate-limit
        imposed by the rates given by the ``RateStrategy``, a
        ``BucketFullException`` is raised.

        This method is called whenever a new access is made. Thus, this we can
        dynamically return different rates, e.g. depending on the number of
        items already in the ``Bucket``.

        :param name: The domain name being accessed.
        :param weight: The additional weight-parameter given to the access.
            Defaults to 1.
        :param bucket: The pyrate-limiter ``Bucket`` that is collecting all of
            the (recent) events on this domain name. If this is the first
            access on this domain, ``bucket`` will be `None`.
        """
        ...


def get_simple_weight_strategy(base_weight: int = 20) -> WeightStrategy:
    """
    A very simple ``WeightStrategy`` that simply assigns a base weight,
    multiplied by the weight modifier given with the access.
    """
    return lambda name, weight, bucket: weight * base_weight


class MultiBucketFactory(BucketFactory):
    def __init__(
        self,
        clock: AbstractClock,
        rate_strategy: RateStrategy,
        weight_strategy: WeightStrategy,
    ) -> None:
        self.clock = clock
        self.rate_strategy = rate_strategy
        self.weight_strategy = weight_strategy
        self.buckets: dict[str, AbstractBucket] = dict()

    def create(
        self,
        clock: AbstractClock,
        bucket_class: Type[AbstractBucket],
        *args,
        **kwargs,
    ) -> AbstractBucket:
        """Creating a bucket dynamically"""
        bucket = bucket_class(*args, **kwargs)
        self.schedule_leak(bucket, clock)
        return bucket

    def wrap_item(self, name: str, weight: int = 1) -> RateItem:
        """Time-stamping item, return a RateItem"""
        now = self.clock.now()
        bucket = self.buckets.get(name, None)
        return RateItem(
            name=name,
            timestamp=now,
            weight=self.weight_strategy(name=name, weight=weight, bucket=bucket),
        )

    def get(self, item: RateItem) -> AbstractBucket:
        if item.name not in self.buckets:
            # Use `self.create(..)` method to both initialize new bucket and calling `schedule_leak` on that bucket
            # We can create different buckets with different types/classes here as well
            new_bucket = self.create(
                clock=self.clock,
                bucket_class=InMemoryBucket,
                rates=self.rate_strategy(item.name),
            )
            self.buckets.update({item.name: new_bucket})

        return self.buckets[item.name]


def get_simple_multibucket_limiter(
    max_rate_per_second: int = 100, base_weight: int = 20
) -> Limiter:
    """
    A simple rate limiting strategy that limits accesses to five per second and
    50 per minute, per domain.
    """
    return Limiter(
        MultiBucketFactory(
            clock=TimeClock(),
            rate_strategy=get_simple_rate_strategy(max_rate_per_second),
            weight_strategy=get_simple_weight_strategy(base_weight),
        )
    )


def domain_mapper(url: str, *args, **kwargs) -> tuple[str, int]:
    """
    Return the domain name and a weight from the given URL.

    The weight is used to indicate how costly the particular URL is to access
    and affects how quickly the rate limiter kicks in. Currently, this weight
    is always 1.
    """
    url_parsed = urlparse(url)
    return url_parsed.hostname or "", 1
