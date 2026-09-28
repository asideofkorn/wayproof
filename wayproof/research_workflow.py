"""Resolve research review facts from an approved, merged GitHub PR.

No serialized receipt is an approval. Revalidate its GitHub review and local Git
ancestry before reading the exact reviewed blob. This adapter never fetches media.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess

from .public_research import ContentReview
from .media_contract import _typed


@dataclass(frozen=True)
class ReviewReceipt:
    pull_request: int
    head_commit: str
    review_path: str


class GitHubResearchReviews:
    """Trusted application configuration; repository/base cannot come from a draft."""
    def __init__(self, checkout: Path, repository: str, base='main', *, maintainers=()):
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repository):
            raise ValueError('invalid configured GitHub repository')
        if isinstance(maintainers, str):
            raise ValueError('maintainers must be a collection of identities')
        maintainers = tuple(maintainers)
        if any(
                not isinstance(login, str) or not re.fullmatch(r'[A-Za-z0-9-]+', login)
                for login in maintainers):
            raise ValueError('invalid configured maintainer identities')
        self.maintainers = frozenset(login.casefold() for login in maintainers)
        self.checkout, self.repository, self.base = Path(checkout), repository, base

    def _git(self, *args):
        return subprocess.run(['git', *args], cwd=self.checkout, check=True,
                              capture_output=True, text=True).stdout

    def _api(self, suffix):
        return json.loads(subprocess.run(
            ['gh', 'api', f'repos/{self.repository}/{suffix}'], check=True,
            capture_output=True, text=True).stdout)

    def resolve(self, receipt: ReviewReceipt, fingerprint: str) -> ContentReview:
        if (type(receipt.pull_request) is not int or receipt.pull_request <= 0 or
                not re.fullmatch('[0-9a-f]{40}', receipt.head_commit) or
                receipt.review_path != f'research-reviews/{fingerprint}.json' or
                not re.fullmatch('[0-9a-f]{64}', fingerprint)):
            raise ValueError('invalid research review receipt')
        pr = self._api(f'pulls/{receipt.pull_request}')
        if (not pr['merged'] or pr['base']['ref'] != self.base or
                pr['base']['repo']['full_name'] != self.repository or
                pr['head']['sha'] != receipt.head_commit):
            raise ValueError('research review is not from the configured merged PR')
        merge = pr['merge_commit_sha']
        if not re.fullmatch('[0-9a-f]{40}', merge or ''):
            raise ValueError('invalid merge identity')
        self._git('merge-base', '--is-ancestor', merge, f'refs/remotes/origin/{self.base}')
        merger = (pr.get('merged_by') or {}).get('login')
        merged_by_maintainer = (isinstance(merger, str) and
                                merger.casefold() in self.maintainers)
        if not merged_by_maintainer:
            self._require_independent_approval(receipt, pr)
        value = json.loads(self._git('show', f'{receipt.head_commit}:{receipt.review_path}'))
        result = _typed(ContentReview, value)
        if result.fingerprint != fingerprint or result.disposition != 'accepted':
            raise ValueError('review does not accept the exact research snapshot')
        return result

    def _require_independent_approval(self, receipt, pr):
        # Paginate reviews: an old approval cannot mask a later dismissal/change request.
        reviews, page = [], 1
        while True:
            batch = self._api(f'pulls/{receipt.pull_request}/reviews?per_page=100&page={page}')
            reviews.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        latest = {}
        for review in sorted(reviews, key=lambda r: r['id']):
            if review['state'] in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
                latest[review['user']['login']] = review
        authorized = False
        for login, review in latest.items():
            if not re.fullmatch(r'[A-Za-z0-9-]+', login) or login == pr['user']['login']:
                continue
            permission = self._api(f'collaborators/{login}/permission').get('role_name')
            if permission not in ('admin', 'maintain'):
                continue
            if review['state'] == 'CHANGES_REQUESTED':
                raise ValueError('maintainer requested changes')
            authorized |= (review['state'] == 'APPROVED' and
                           review['commit_id'] == receipt.head_commit)
        if not authorized:
            raise ValueError('no current-head maintainer approval')
