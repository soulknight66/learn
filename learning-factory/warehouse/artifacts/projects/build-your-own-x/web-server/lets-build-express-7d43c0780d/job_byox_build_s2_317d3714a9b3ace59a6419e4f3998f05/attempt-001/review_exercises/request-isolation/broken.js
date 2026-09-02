'use strict';

let activeIdentifier;

async function handleJob(req, res) {
  activeIdentifier = req.params.id;
  await new Promise((resolve) => setTimeout(resolve, Number(req.params.delay)));
  res.json({
    startedAs: req.params.id,
    finishedAs: activeIdentifier
  });
}

module.exports = { handleJob };
