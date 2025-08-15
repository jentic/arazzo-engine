# Contributing to Arazzo Engine

Thank you for considering contributing to the Arazzo Engine! 
This document outlines the process for contributing to the Arazzo Engine Repository.

## How to Contribute

Contributing to an open source project doesn't have to be through code alone. There are various ways in which you can contribute, and we're happy to accept all kinds of help. This guide will give you information on what kind of contributions you can make, and what steps you should follow.

### Opening issues

Filing issues with the project is a great step in helping the project — you're helping us
learn what's not working, what you might want to see in the project or what we can do better.
Even questions like 'how do I do X?' help us know where documentation may be lacking. When opening an issue, please make sure to follow the issue templates. Doing that helps us gather the required initial information to be able to further assist.

### Commenting

Adding meaningful comments to issues and pull requests, helps the community as a whole.
Providing suggestions, helping to solve issues, giving feedback — it all helps. Once again,
the main guideline we have here is `be kind`.

### Voting

We're not big fans of adding comments like "+1", or "any updates on this?" 
but adding a 👍 reaction to the opening comment helps us track what attracts
more interest in our community, and what we should focus on next.

### Code reviews

Even if you don't have time to contribute your own code, 
you may have time to review existing pull requests, helping us process those faster.

### Documentation

Improving the project documentation is a huge help. You don't need to be an expert in the project,
or understand all the bits and pieces. Have you dealt with an issue and think that
if there was better documentation it'd have been easier? Document that part!
If you tried going through the documentation and found it hard to navigate — fix that!

## Code Contributions

### Code Contribution Types

Code changes can come in several forms, and the way they're handled differ.

#### Documentation

For the most part, documentation PRs would be accepted after an initial review.
Be aware that a large documentation change may require longer review and potentially a discussion.

#### Bug fixes

Bug fixes are always welcome as PRs. If you found a bug and would like to fix it,
it's almost always better to open a ticket describing the issue alongside the PR solving it.
Sometimes, bug fixes can be controversial. If you think this may happen with your fix,
please start a discussion through a ticket before filing an actual fix.

#### Features

Adding features is a great way to improve an open source project.
That said, each project has its own roadmap, requirements, constraints and needs. 
Before submitting a PR for _any_ feature, please file an issue first describing
the change you want to make, and wait for feedback. Trying to analyze a feature contribution 
directly through a pull request is stressful for both sides, and a lot of concerns
can be avoided by having an initial discussion.

### Coding Guidelines

#### Branching model

- Feature branches should be prefixed with `feature/`.
- Bugfix branches should be prefixed with `fix/`.
- After the forward slash, include a short description of what you're fixing. For example: `fix/fix-everything-that-was-broken`.
- If there's an issue filed that you're addressing in your branch, include the issue number directly after the forward slash. For example: `fix/1234-fix-all-the-other-things`.

#### Committing

- Break your commits into logical atomic units. Well-segmented commits make it _much_ easier for others to step through your changes.
- Limit your subject (first) line to 69 characters (GitHub truncates more than 70).
- Use the imperative, present tense: "change" not "changed" nor "changes"
- Don't use [magic GitHub words](https://help.github.com/articles/closing-issues-using-keywords/) in your commits to close issues - do that in the pull request for your code instead.
- Use `Refs #<issue-number>` in your commit messages to link to the issue you're addressing. This will help maintainers track the changes related to that issue.
- Use [Developer Certificate of Origin](https://git-scm.com/docs/git-commit#Documentation/git-commit.txt--s)
- Read [Conventional Commits Specification](https://www.conventionalcommits.org/en/v1.0.0/) before creating your first commit

#### Making pull requests

1.  **Find or Create an Issue:** Before starting, check if an issue for your proposed change already exists. If not, please create a new one.
    *   For **new features or significant changes**, please detail what you aim to accomplish and your planned technical approach.
    *   For **bug fixes**, describe the bug and how you plan to fix it.

2.  **Fork & Branch:** Create a fork of the repository and make your changes in a descriptively named branch.

3.  **Code & Test:** Write your code and add tests to cover your changes. Make sure the existing test suite passes.

4.  **Update Documentation:** If you've added a new feature or changed an existing one, be sure to update the relevant documentation.

5.  **Submit a Pull Request:** When you're ready, submit a pull request.
    *   Provide a clear summary of the changes you've made.
    *   Include references to issues that your PR solves, and use [magic GitHub words](https://help.github.com/articles/closing-issues-using-keywords/) to close those issues automatically when your PR is merged. Add the references in the PR body and not the title.

6.  **Review and Merge:** The PR will be reviewed by maintainers, who may request changes if necessary. Once approved, your PR will be merged.

To make the review process as efficient as possible, please try to keep your pull requests **small and focused**. We also typically **squash commits** when merging a PR to maintain a clean and readable git history.

#### Merging pull requests

- **Prefer** using GitHub's `Squash and merge` strategy.
- **Do** follow the [Conventional Commits](https://conventionalcommits.org) standard format for your squash commit.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Submitting Issues

We use GitHub Issues for all bug reports and feature requests. Before opening a new issue, please search the existing issues to see if your problem or idea has already been discussed.

When you're ready, please use our issue templates to create a report:

-   **[🐛 Bug Report](https://github.com/jentic/arazzo-engine/issues/new?assignees=&labels=bug&template=bug_report.md&title=%5BBug%5D+)**
-   **[✨ Feature Request](https://github.com/jentic/arazzo-engine/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=%5BFeature%5D+)**

This helps us stay organized and ensures we have all the information we need to address your submission efficiently. We look forward to your feedback!

## Recognition

Contributors will be recognized in our documentation and through appropriate credit mechanisms. We believe in acknowledging all forms of contribution.
Thank you for helping build and improve the Standard Agent!

---

*This document may be updated as the project evolves.*

[comment]: <> (Some of the content in this document is inspired by the https://github.com/swagger-api/.github/blob/master/CONTRIBUTING.md)