# Presentation Script: Term Deposit Predictor

**Data Miners · Group 1.1 · IT3051 Fundamentals of Data Mining**

Use this alongside `docs/Presentation.pptx`. Each slide section below is also copied into that slide's
speaker notes, so it shows up in PowerPoint's Presenter View.

## Who presents what

Each member presents the slides closest to the work they did, and everyone drives one part of the live demo.

| Member | Student ID | Slides | Part of the live demo | Approx. time |
|---|---|---|---|---|
| Gunathilaka W.A.D.S. | IT23859456 | 1 Title, 2 Problem, 3 Solution, 4 Value | Batch (CSV) scoring | ~4 min |
| Edirisinghe E.M.K.L. | IT23857780 | 5 How it works, 6 What the data told us, 11 What drives a prediction | EDA page | ~4 min |
| Illesinghe E.S. | IT23557024 | 8 Calling by score, 9 Tuning the cut-off, 10 Model choice | Models page | ~4 min |
| Kaluarachchi R.G. | IT23544918 | 7 Live demo intro, 12 Trust, 13 Next steps, 15 Closing | Home page and single-client prediction | ~4 min |
| Everyone | | 14 The team (one sentence each) | | ~1 min |

Total: about 17 minutes, including a 4-minute demo. To cut down to about 12 minutes, shorten the demo to
two pages (single prediction and batch) and skip slide 11.

Conventions: *italics in brackets* are stage directions, not to be read out. **Handover** lines pass to the
next speaker.

---

## Slide 1 · Title

**Speaker:** Gunathilaka W.A.D.S. · ~45 s

Good morning everyone. We are Data Miners, Group 1.1. I'm Gunathilaka, and with me are Edirisinghe,
Illesinghe and Kaluarachchi.

Our project is the Term Deposit Predictor. In one line: it helps a bank's call team phone the clients who
are most likely to say yes first.

Over the next few minutes we'll show you the problem, how we solved it, a live demo of the system, and what
the results mean for the bank.

---

## Slide 2 · The problem

**Speaker:** Gunathilaka W.A.D.S. · ~1 min

We worked with real data from a Portuguese bank's telemarketing campaigns between 2008 and 2010. That's
45,211 phone calls, each one asking a client to open a term deposit.

*[Point to the dot grid.]* Each dot here is one percent of those calls. Only the blue ones, about 12 out of
100, or 11.7%, ended with the client saying yes.

So nearly nine in ten calls end in a no. If agents simply work down the list, most of their day goes on
clients who were never going to say yes, and those clients get annoyed by calls they didn't want.

---

## Slide 3 · Our solution

**Speaker:** Gunathilaka W.A.D.S. · ~45 s

Our answer is to score every client before the call is made, so the team can phone the most promising
people first.

The system does three things. You can score one client by filling in a short form and get an instant yes or
no with a likelihood. You can upload a whole call list as a CSV file and get it back sorted from most to
least promising. And you can see which kinds of clients, and which timing, tend to lead to a yes.

---

## Slide 4 · The value

**Speaker:** Gunathilaka W.A.D.S. · ~45 s

For the bank, this means four things.

Fewer wasted calls, because agents spend their time on likely buyers. More sales from the same effort:
calling just the top 20% of the ranked list reaches 63% of everyone who would subscribe. Smarter campaign
timing, because the data shows when to call and when not to bother. And it's kinder to clients, with fewer
repeat calls to people who aren't interested.

**Handover:** Edirisinghe will now explain how the system works and what the data told us.

---

## Slide 5 · How it works

**Speaker:** Edirisinghe E.M.K.L. · ~1 min

Thank you. The system works in four steps.

First, it learns from the 45,211 past calls, where we know the outcome of every one.

Second, we cleaned the data and kept it fair. We checked for missing values, duplicates and invalid values.
Most importantly, we removed call duration. It's a very strong predictor, but you only know it after the
call has ended, so using it would be cheating.

Third, we trained and compared six different models, all tuned and tested in exactly the same way.

Fourth, the best model is served through a web dashboard and an API that gives predictions on demand.

The winning model is Gradient Boosting. It builds many small decision trees, each one correcting the
mistakes of the ones before it.

---

## Slide 6 · What the data told us

**Speaker:** Edirisinghe E.M.K.L. · ~1 min 30 s

Before modelling, we explored the data to see who actually says yes. Each bar is the share of a group that
subscribed, and the dashed line is the 11.7% average.

*[Point to the top bar.]* The strongest signal is history. Clients who said yes in the previous campaign
subscribe 64.7% of the time, which is 5.5 times the average.

Timing matters a lot as well. Calls in March succeed 52% of the time and in September 46.5%. But look at
May: 30% of all calls were made in May, when only 6.7% said yes. The bank was calling most in its worst
month.

Some groups are more receptive: clients over 65 at 42.6% and students at 28.7%. Being reached on a mobile
also helps.

At the bottom, repeated calling clearly hurts. After ten or more calls in a campaign, only 4.2% say yes.

So the headline is that when and how you call matters most.

**Handover:** Kaluarachchi will now take you through a live demo of the system.

---

## Slide 7 · Live demo (about 4 minutes)

*[Switch from the slides to the browser with the dashboard already open on the Home page. Each member drives
their own part. If the live system fails, use backup slides 16 to 20.]*

### Part 1 · Home page and single-client prediction

**Speaker:** Kaluarachchi R.G. · ~1 min 30 s

This is the dashboard. The Home page sums up the tool in one line and shows the model currently serving
predictions, Gradient Boosting, with its key numbers.

*[Click "Prediction", Single client tab.]* Here a call agent fills in what the bank knows about a client
before calling: age, job, finances, and contact history. The form is generated from the API, so it always
matches what the model expects.

*[Click Predict with the default values.]* This typical client, a 39-year-old blue-collar worker with a
housing loan, called in May and never contacted before, scores about 39%. That's below our 62% cut-off, so
the answer is no, with medium priority.

*[Change Month to "mar", Days since last contact to 90, Previous contacts to 1, Previous outcome to
"success", turn off Housing loan, then click Predict.]* Now the same person said yes in the last campaign,
is being called in March and has no housing loan. The probability jumps to about 94%, a high-priority yes.
That's exactly what the data showed us.

**Handover:** Gunathilaka will show how a whole call list is scored.

### Part 2 · Batch (CSV) scoring

**Speaker:** Gunathilaka W.A.D.S. · ~1 min

*[Click the "Batch (CSV)" tab and upload the prepared CSV file.]* In practice the team doesn't score clients
one at a time. They upload their call list as a CSV.

Every row is scored at once and the list comes back sorted, with the best leads at the top, each with a
probability and a priority. Rows with problems are reported individually instead of breaking the whole
upload.

*[Click "Download CSV".]* The scored list can be downloaded and handed straight to the call team.

**Handover:** Edirisinghe will show the data exploration page.

### Part 3 · EDA page

**Speaker:** Edirisinghe E.M.K.L. · ~45 s

*[Click "EDA".]* This page shows the findings from slide 6 live from the data. At the top are the key
findings, such as previous success at 64.7% and March at 52%. Below are how the data was cleaned and the
interactive charts, where you can see the subscription rate for any group.

**Handover:** Illesinghe will show how the models compare.

### Part 4 · Models page

**Speaker:** Illesinghe E.S. · ~45 s

*[Click "Models".]* This page compares all six models we trained, with their ROC curves, confusion matrix
and the most important features. Gradient Boosting is marked as the selected model. Let me go back to the
slides to explain what these results mean.

*[Switch back to the slides, slide 8.]*

---

## Slide 8 · Findings: calling by score

**Speaker:** Illesinghe E.S. · ~1 min 15 s

The real question for the bank is whether the scores help the team find buyers faster.

To test this fairly, we kept 9,043 clients completely aside. The model never saw them during training.

*[Point to the first row.]* If the team calls in random order, after calling 10% of the list they find 10%
of the subscribers, the grey bar. If they call in our model's order, those first 10% of calls already reach
44% of all subscribers. That's 4.4 times better.

After 20% of calls the model reaches 63% of subscribers, and after 30% it reaches 72%. Most of the yeses are
concentrated at the top of the list.

---

## Slide 9 · Findings: tuning the cut-off

**Speaker:** Illesinghe E.S. · ~1 min 15 s

A model gives each client a score, and we have to choose the cut-off above which we say "call this client".
By default that's 50%. We tuned it to 62% using only the training data.

The result: wasted calls, meaning clients we flagged who then said no, fell from 1,212 to 690. That's 43%
fewer. And the hit rate went up from 36% to 45% of flagged clients actually saying yes.

To be honest about the trade-off: we now find 562 of the 1,058 subscribers instead of 676, about 17% fewer.
That's a business decision. If calls are cheap, the bank can lower the cut-off and find more. If calls are
expensive, it can raise it.

---

## Slide 10 · Model choice

**Speaker:** Illesinghe E.S. · ~1 min 15 s

We compared six models: Gradient Boosting, Random Forest, Logistic Regression, Decision Tree, K-Nearest
Neighbours and Naive Bayes. Each was tuned with cross-validation on the training data.

We chose the winner by ROC-AUC, which measures how well a model ranks likely subscribers above unlikely ones.
Gradient Boosting was best both in cross-validation and on the unseen test data, at 0.806, with Random
Forest close behind.

*[Point to the KNN row.]* This row shows why accuracy alone is misleading. K-Nearest Neighbours has the
highest accuracy at 89%, but it finds only 12% of subscribers. With 88% of answers being no, a model that
almost always says no looks accurate but is useless to the bank.

**Handover:** Edirisinghe will explain what drives the predictions.

---

## Slide 11 · What drives a prediction

**Speaker:** Edirisinghe E.M.K.L. · ~1 min

To see what the model relies on, we shuffled one input at a time and measured how much worse the model got.
The bigger the drop, the more that input matters.

The top three are the month of the call, the contact channel and the outcome of the last campaign. Day of
the month, age, housing loan and balance follow.

This matches what we found when exploring the data. Timing, channel and history matter most, while job,
education and marital status add very little once those are known.

**Handover:** Kaluarachchi will explain why the results can be trusted.

---

## Slide 12 · Trust

**Speaker:** Kaluarachchi R.G. · ~1 min

We designed the system to be honest about what it knows.

First, no peeking at the answer. Call length was removed because it's only known after the call, and every
cleaning step, such as outlier limits, scaling and encoding, learns from the training data only.

Second, it was tested on unseen clients. 20% of the data was locked away until the very end, and the
cross-validation and test scores agree within 0.02, so the model isn't over-fitted.

Third, we're open about its limits. About 45% of flagged clients say yes, so it's not perfect. The scores
rank clients well but aren't exact probabilities.

We also verified the system with 8 automated API tests, a frontend routing test, and manual end-to-end checks
of every page.

---

## Slide 13 · Next steps

**Speaker:** Kaluarachchi R.G. · ~45 s

To take this from a prototype to a real call centre, there are four next steps.

Retrain on recent data, because these calls are from 2008 to 2010 and client behaviour has changed. Put a
price on each call, so the cut-off comes from real call costs and deposit profits. Explain every prediction
by showing the reasons behind each client's score in the dashboard. And ship it securely, with login, cloud
hosting and monitoring.

---

## Slide 14 · The team

**Speaker:** each member says their own line · ~1 min

**Kaluarachchi R.G.:** Each of us owned one stage of the project and contributed 25%. I built the FastAPI
backend, the Home and prediction pages, the app shell and the automated tests.

**Gunathilaka W.A.D.S.:** I handled downloading and cleaning the data, the data leakage checks, and batch CSV
scoring.

**Edirisinghe E.M.K.L.:** I did the exploratory analysis, feature engineering, outlier capping, and the EDA
page.

**Illesinghe E.S.:** I trained and compared the six models, tuned the cut-off, measured feature importance,
and built the Models page and training report.

---

## Slide 15 · In one sentence

**Speaker:** Kaluarachchi R.G. · ~30 s

So, in one sentence: our predictor tells the call team who to phone first, reaching 44% of subscribers in the
first 10% of calls.

Thank you for listening. We're happy to take your questions.

---

## Backup slides (16 to 21)

- **Slides 16 to 20:** screenshots of each page. Use them if the live demo fails, with the same speakers as in
  the demo.
- **Slide 21:** full results table with every metric for every model. Illesinghe uses it for detailed
  questions about the models.

## Likely questions, and who answers

| Question | Answered by |
|---|---|
| Why did you remove call duration? | Gunathilaka |
| How did you handle the "unknown" values and missing data? | Gunathilaka |
| What features did you engineer, and why? | Edirisinghe |
| How did you deal with outliers and the class imbalance? | Edirisinghe (outliers), Illesinghe (imbalance: balanced class weights) |
| Why ROC-AUC and not accuracy? | Illesinghe |
| How did you choose 0.62 as the cut-off? | Illesinghe (best F1 on out-of-fold training predictions, never the test set) |
| Is the model over-fitted? | Illesinghe (cross-validation and test scores differ by at most 0.02) |
| How does the API validate input? What happens with a bad CSV row? | Kaluarachchi (HTTP 422 for bad fields; bad CSV rows reported one by one) |
| How would this run in production? | Kaluarachchi |
